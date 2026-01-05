"""Search entrypoints for the PriceScout backend."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, Iterable, List

from openai_search import rewrite_query_with_vendors, summarize_offers_with_openai
from scrapers.fixez import scrape_fixez
from scrapers.google_search import scrape_google_search
from scrapers.laptopscreen import scrape_laptopscreen
from scrapers.mengtor import scrape_mengtor
from scrapers.mobilesentrix import scrape_mobilesentrix
from scrapers.websearch import scrape_websearch

logger = logging.getLogger(__name__)

Scraper = Callable[[str], Iterable[Dict[str, object]]]

PRIORITY_VENDORS = ("mobilesentrix", "amazon", "ebay")


SCRAPER_SOURCES: List[tuple[str, Scraper]] = [
    ("MobileSentrix", scrape_mobilesentrix),
    ("Fixez", scrape_fixez),
    ("Mengtor", scrape_mengtor),
    ("Laptopscreen", scrape_laptopscreen),
    ("Google", scrape_google_search),
    ("Web", scrape_websearch),
]


def _run_scrapers(query: str) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    ordered_results: Dict[int, List[Dict[str, object]]] = {}

    with ThreadPoolExecutor(max_workers=len(SCRAPER_SOURCES)) as executor:
        future_map = {
            executor.submit(lambda s=scraper: list(s(query))): (index, name)
            for index, (name, scraper) in enumerate(SCRAPER_SOURCES)
        }

        for future in as_completed(future_map):
            index, name = future_map[future]
            try:
                scraper_results = future.result()
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Error scraping %s", name)
                continue

            logger.info("%s returned %d items", name, len(scraper_results))
            ordered_results[index] = scraper_results

    for index in range(len(SCRAPER_SOURCES)):
        results.extend(ordered_results.get(index, []))

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


def search_products(query: str) -> List[Dict[str, object]]:
    """Return search results for *query*.

    All vendor scrapers are queried to provide real product listings from the
    supported sites. This avoids fabricated AI responses and ensures we always
    return the concrete offers we can scrape.
    """

    if not query.strip():
        return []

    rewritten = rewrite_query_with_vendors(query)
    queries = [rewritten.get("primary", query)] + list(rewritten.get("boosted", []))

    results: List[Dict[str, object]] = []
    for variant in queries:
        results.extend(_run_scrapers(variant))

    deduped = _deduplicate_results(results)
    sorted_results = _sort_results_by_priority(deduped)
    return summarize_offers_with_openai(query, sorted_results)

