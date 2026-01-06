"""Search entrypoints for the PriceScout backend."""

from __future__ import annotations

import logging
import os
import time
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

MAX_QUERY_VARIANTS = int(os.environ.get("MAX_QUERY_VARIANTS", "2"))
MAX_SEARCH_SECONDS = float(os.environ.get("MAX_SEARCH_SECONDS", "30"))


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
    for name, scraper in SCRAPER_SOURCES:
        try:
            scraper_results = list(scraper(query))
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Error scraping %s", name)
            continue

        logger.info("%s returned %d items", name, len(scraper_results))
        results.extend(scraper_results)

    return results


def _query_variants(original_query: str) -> List[str]:
    """Return a bounded list of unique query variants for scraping."""

    rewritten = rewrite_query_with_vendors(original_query)
    candidates = [rewritten.get("primary", original_query), *rewritten.get("boosted", [])]

    variants: List[str] = []
    seen = set()
    for candidate in candidates:
        variant = str(candidate or "").strip()
        if not variant:
            continue
        key = variant.lower()
        if key in seen:
            continue
        seen.add(key)
        variants.append(variant)
        if len(variants) >= MAX_QUERY_VARIANTS:
            break

    return variants


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

    results: List[Dict[str, object]] = []
    deadline = time.monotonic() + MAX_SEARCH_SECONDS

    for variant in _query_variants(query):
        if time.monotonic() >= deadline:
            logger.warning("Search deadline reached before running variant '%s'", variant)
            break

        results.extend(_run_scrapers(variant))

        if time.monotonic() >= deadline:
            logger.warning("Search deadline reached after variant '%s'", variant)
            break

    deduped = _deduplicate_results(results)
    sorted_results = _sort_results_by_priority(deduped)
    return summarize_offers_with_openai(query, sorted_results)

