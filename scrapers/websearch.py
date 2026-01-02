"""Web search scraper used as a lightweight fallback."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from scrapers.utils import safe_get

logger = logging.getLogger(__name__)

SEARCH_URL = "https://duckduckgo.com/html/"
MAX_RESULTS = 10


def _domain_for(url: str) -> str:
    try:
        parsed = urlparse(url)
        return parsed.netloc or "Web"
    except Exception:  # pragma: no cover - defensive
        return "Web"


def _parse_results(html: str) -> List[Dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, object]] = []

    for block in soup.select("div.result"):
        link_el = block.select_one("a.result__a")
        if not link_el:
            continue

        href = link_el.get("href")
        if not href:
            continue

        title = link_el.get_text(" ", strip=True)
        snippet_el = block.select_one("div.result__snippet") or block.select_one(
            "a.result__snippet"
        )
        snippet = snippet_el.get_text(" ", strip=True) if snippet_el else None

        results.append(
            {
                "title": title,
                "link": href,
                "source": _domain_for(href),
                "in_stock": False,
                "price": None,
                "image": None,
                "snippet": snippet,
                "stock_label": "Visit site",
            }
        )

        if len(results) >= MAX_RESULTS:
            break

    return results


def scrape_websearch(query: str) -> Iterable[Dict[str, object]]:
    """Perform a simple DuckDuckGo HTML search for *query*.

    Results are returned in the same shape as scraper outputs so they can be
    rendered by the UI alongside structured vendor listings.
    """

    if not query.strip():
        return []

    html = safe_get(SEARCH_URL, params={"q": query, "kl": "us-en"})
    if not html:
        logger.warning("Web search did not return HTML for query '%s'", query)
        return []

    return _parse_results(html)
