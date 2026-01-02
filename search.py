"""Search entrypoints for the PriceScout backend."""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from typing import Callable, Dict, Iterable, List

from scrapers.fixez import scrape_fixez
from scrapers.laptopscreen import scrape_laptopscreen
from scrapers.mengtor import scrape_mengtor
from scrapers.mobilesentrix import scrape_mobilesentrix
from scrapers.websearch import scrape_websearch

logger = logging.getLogger(__name__)

Scraper = Callable[[str], Iterable[Dict[str, object]]]


SCRAPER_SOURCES: List[tuple[str, Scraper]] = [
    ("MobileSentrix", scrape_mobilesentrix),
    ("Fixez", scrape_fixez),
    ("Mengtor", scrape_mengtor),
    ("Laptopscreen", scrape_laptopscreen),
    ("Web", scrape_websearch),
]


def _run_scrapers(query: str) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    for name, scraper in SCRAPER_SOURCES:
        try:
            scraper_results = list(scraper(query))
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Error scraping %s", name)
            continue

        logger.info("%s returned %d items", name, len(scraper_results))
        results.extend(scraper_results)

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


def _normalize_tokens(text: str) -> List[str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    if not normalized:
        return []
    return [token for token in normalized.split(" ") if token]


def _score_result(query_tokens: List[str], query_key: str, item: Dict[str, object]) -> float:
    title = str(item.get("title", ""))
    title_tokens = _normalize_tokens(title)
    if not title_tokens:
        return 0.0

    collapsed_title = re.sub(r"[^a-z0-9]+", "", title.lower())

    matched = 0
    for token in query_tokens:
        if token in title_tokens or token in collapsed_title:
            matched += 1

    coverage = matched / len(query_tokens) if query_tokens else 0.0
    density = matched / len(title_tokens)

    sequence_ratio = SequenceMatcher(None, query_key, collapsed_title).ratio()

    accessory_keywords = {
        "cable",
        "cables",
        "button",
        "buttons",
        "guide",
        "manual",
        "spec",
        "specification",
        "tutorial",
        "housing",
        "shell",
        "strap",
        "case",
    }

    penalty_tokens = [token for token in title_tokens if token not in query_tokens]
    accessory_penalty = sum(1 for token in penalty_tokens if token in accessory_keywords)

    score = 0.5 * coverage + 0.2 * density + 0.3 * sequence_ratio
    score -= 0.08 * accessory_penalty
    score -= min(0.2, 0.02 * len(penalty_tokens))

    return max(score, 0.0)


def _filter_closest_matches(results: List[Dict[str, object]], query: str) -> List[Dict[str, object]]:
    query_tokens = _normalize_tokens(query)
    query_key = re.sub(r"[^a-z0-9]+", "", query.lower())

    if not query_tokens or not query_key:
        return results

    scored: List[tuple[float, Dict[str, object]]] = []
    for item in results:
        score = _score_result(query_tokens, query_key, item)
        scored.append((score, item))

    if not scored:
        return results

    best_score = max(score for score, _ in scored)
    if best_score < 0.6:
        return results

    threshold = best_score - 0.05

    filtered = [item for score, item in scored if score >= threshold]

    if filtered:
        return filtered

    # Fallback to the single best match when filtering removes everything.
    scored.sort(key=lambda entry: entry[0], reverse=True)
    return [scored[0][1]]


def search_products(query: str) -> List[Dict[str, object]]:
    """Return search results for *query*.

    All vendor scrapers are queried to provide real product listings from the
    supported sites. This avoids fabricated AI responses and ensures we always
    return the concrete offers we can scrape.
    """

    if not query.strip():
        return []

    results = _run_scrapers(query)
    deduped = _deduplicate_results(results)
    return _filter_closest_matches(deduped, query)

