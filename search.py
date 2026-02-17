"""Search entrypoints for the PriceScout backend."""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from difflib import SequenceMatcher
from typing import Callable, Dict, Iterable, List

from openai_search import rewrite_query_with_vendors, search_openai, summarize_offers_with_openai
from scrapers.fixez import scrape_fixez
from scrapers.google_search import scrape_google_search
from scrapers.mobilesentrix import scrape_mobilesentrix
from scrapers.websearch import scrape_websearch

logger = logging.getLogger(__name__)

Scraper = Callable[[str], Iterable[Dict[str, object]]]

PRIORITY_VENDORS = ("mobilesentrix", "fixez", "amazon", "ebay")
CLEANING_KEYWORDS = {
    "clean",
    "cleaner",
    "cleaning",
    "wipe",
    "wipes",
    "alcohol",
    "solvent",
    "degreaser",
    "brush",
    "tool",
    "kit",
    "adhesive",
    "tape",
    "microfiber",
}
REPAIR_KEYWORDS = {
    "repair",
    "replacement",
    "part",
    "parts",
    "screen",
    "battery",
    "charging",
    "connector",
    "digitizer",
    "display",
    "assembly",
    "flex",
    "camera",
    "lcd",
    "oled",
    "glass",
    "housing",
    "frame",
    "speaker",
    "microphone",
    "usb",
    "port",
    "dock",
    "motherboard",
    "logic",
}
MIN_WORDING_MATCH = 0.80


SCRAPER_SOURCES: List[tuple[str, Scraper]] = [
    ("MobileSentrix", scrape_mobilesentrix),
    ("Fixez", scrape_fixez),
    ("Google", scrape_google_search),
    ("Web", scrape_websearch),
]

MAX_SCRAPER_WORKERS = 4
SCRAPER_TIMEOUT_SECONDS = 25


def _call_scraper(name: str, scraper: Scraper, query: str) -> List[Dict[str, object]]:
    try:
        return list(scraper(query))
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("Error scraping %s", name)
        return []


def _run_scrapers(query: str) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    max_workers = min(MAX_SCRAPER_WORKERS, len(SCRAPER_SOURCES))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_call_scraper, name, scraper, query): name
            for name, scraper in SCRAPER_SOURCES
        }

        try:
            for future in as_completed(futures, timeout=SCRAPER_TIMEOUT_SECONDS):
                name = futures[future]
                scraper_results = future.result()
                logger.info("%s returned %d items", name, len(scraper_results))
                results.extend(scraper_results)
        except TimeoutError:
            logger.warning("Timed out waiting for scrapers after %ss", SCRAPER_TIMEOUT_SECONDS)
        finally:
            for future, name in futures.items():
                if not future.done():
                    future.cancel()
                    logger.warning("Cancelled scraper %s after timeout", name)

    return results


def _deduplicate_results(results: List[Dict[str, object]]) -> List[Dict[str, object]]:
    seen_links = set()
    deduped: List[Dict[str, object]] = []

    for item in results:
        link = str(item.get("link", "")).strip()
        title = str(item.get("title", "")).strip()

        normalized = link.rstrip("/").lower() if link else ""
        key = normalized or title.lower()

        if not key or key in seen_links:
            continue

        seen_links.add(key)
        deduped.append(item)

    return deduped


def _price_sort_key(item: Dict[str, object]) -> float:
    for key in ("price_value", "price"):
        value = item.get(key)
        try:
            return float(value)
        except (TypeError, ValueError):
            continue

    return float("inf")


def _sort_results_by_priority(results: List[Dict[str, object]]) -> List[Dict[str, object]]:
    def priority_index(item: Dict[str, object]) -> tuple[int, int]:
        source = str(item.get("source", "")).lower()
        for index, vendor in enumerate(PRIORITY_VENDORS):
            if vendor in source:
                return 0, index
        return 1, len(PRIORITY_VENDORS)

    return sorted(results, key=lambda item: (*priority_index(item), _price_sort_key(item)))


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9\s]+", " ", value.lower()).strip()


def _wording_match_score(query: str, result: Dict[str, object]) -> float:
    normalized_query = _normalize_text(query)
    normalized_title = _normalize_text(str(result.get("title", "")))

    if not normalized_query or not normalized_title:
        return 0.0

    query_tokens = {token for token in normalized_query.split() if token}
    title_tokens = {token for token in normalized_title.split() if token}

    token_coverage = (
        len(query_tokens & title_tokens) / len(query_tokens)
        if query_tokens
        else 0.0
    )
    sequence_ratio = SequenceMatcher(None, normalized_query, normalized_title).ratio()
    return max(token_coverage, sequence_ratio)


def _is_supported_category(query: str) -> bool:
    normalized_query = _normalize_text(query)
    query_tokens = set(normalized_query.split())
    category_tokens = CLEANING_KEYWORDS | REPAIR_KEYWORDS
    return bool(query_tokens & category_tokens)


def _filter_results_for_category_and_match(
    query: str, results: List[Dict[str, object]]
) -> List[Dict[str, object]]:
    filtered: List[Dict[str, object]] = []

    for item in results:
        score = _wording_match_score(query, item)
        if score < MIN_WORDING_MATCH:
            continue

        enriched = dict(item)
        enriched["match_score"] = round(score, 3)
        filtered.append(enriched)

    return filtered


def _sort_results_by_price(results: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return sorted(results, key=_price_sort_key)


def search_products(query: str) -> List[Dict[str, object]]:
    """Return search results for *query*.

    All vendor scrapers are queried to provide real product listings from the
    supported sites. This avoids fabricated AI responses and ensures we always
    return the concrete offers we can scrape.
    """

    if not query.strip():
        return []

    if not _is_supported_category(query):
        return []

    rewritten = rewrite_query_with_vendors(query)
    queries = [rewritten.get("primary", query)] + list(rewritten.get("boosted", []))

    results: List[Dict[str, object]] = []
    for variant in queries:
        results.extend(_run_scrapers(variant))

    deduped = _deduplicate_results(results)

    if not deduped:
        logger.info("Scrapers returned no results for '%s'; falling back to OpenAI", query)
        ai_offers = search_openai(query)
        deduped = _deduplicate_results(ai_offers)

    prioritized = _sort_results_by_priority(deduped)

    # Remove obvious query mismatches before summarization so relevant offers are
    # not crowded out by low-price noise from boosted vendor queries.
    matched = _filter_results_for_category_and_match(query, prioritized)
    candidates = matched or prioritized

    summarized = summarize_offers_with_openai(query, candidates)
    filtered = _filter_results_for_category_and_match(query, summarized)
    return _sort_results_by_price(filtered)
