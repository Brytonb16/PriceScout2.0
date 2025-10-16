"""Search entrypoints for the PriceScout backend."""

from __future__ import annotations

import logging
from typing import Callable, Dict, Iterable, List

from openai_search import search_openai
from scrapers.fixez import scrape_fixez
from scrapers.laptopscreen import scrape_laptopscreen
from scrapers.mengtor import scrape_mengtor
from scrapers.mobilesentrix import scrape_mobilesentrix

logger = logging.getLogger(__name__)

Scraper = Callable[[str], Iterable[Dict[str, object]]]


SCRAPER_SOURCES: List[tuple[str, Scraper]] = [
    ("MobileSentrix", scrape_mobilesentrix),
    ("Fixez", scrape_fixez),
    ("Mengtor", scrape_mengtor),
    ("Laptopscreen", scrape_laptopscreen),
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


def search_products(query: str) -> List[Dict[str, object]]:
    """Return search results for *query*.

    The OpenAI backend is attempted first to supply rich cross-site matches.
    If that returns no items (or fails), the legacy scrapers are invoked as a
    fallback so the frontend still receives data.
    """

    if not query.strip():
        return []

    ai_results = []
    try:
        ai_results = list(search_openai(query))
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("OpenAI search failed")

    if ai_results:
        return ai_results

    logger.info("OpenAI returned no results; falling back to scrapers")
    return _run_scrapers(query)

