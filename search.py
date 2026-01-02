"""Search entrypoints for the PriceScout backend."""

from __future__ import annotations

import logging
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


def search_products(query: str) -> List[Dict[str, object]]:
    """Return search results for *query*.

    All vendor scrapers are queried to provide real product listings from the
    supported sites. This avoids fabricated AI responses and ensures we always
    return the concrete offers we can scrape.
    """

    if not query.strip():
        return []

    results = _run_scrapers(query)
    return _deduplicate_results(results)

