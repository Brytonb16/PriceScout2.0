"""Lightweight Google search scraper to complement DuckDuckGo results."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from scrapers.utils import parse_price, safe_get

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.google.com/search"
MAX_RESULTS = 10


def _domain_for(url: str) -> str:
    try:
        return urlparse(url).netloc or "Web"
    except Exception:  # pragma: no cover - defensive
        return "Web"


def _parse_results(html: str) -> List[Dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, object]] = []

    for card in soup.select("div.g, div.MjjYud"):
        link_el = card.select_one("a")
        title_el = card.select_one("h3")
        if not link_el or not title_el:
            continue

        href = link_el.get("href")
        title = title_el.get_text(" ", strip=True)
        if not href or not title:
            continue

        source = _domain_for(href)
        snippet_el = card.select_one("div.VwiC3b") or card.select_one("div.IsZvec")
        snippet = snippet_el.get_text(" ", strip=True) if snippet_el else None

        results.append(
            {
                "title": title,
                "link": href,
                "source": source,
                "snippet": snippet,
                "image": None,
                "in_stock": False,
                "price": None,
                "stock_label": "Visit site",
            }
        )

        if len(results) >= MAX_RESULTS:
            break

    return results


def _parse_prices_from_shopping(html: str) -> List[Dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    listings: List[Dict[str, object]] = []

    for product in soup.select("div.sh-dgr__content"):
        title_el = product.select_one("h3, div.EI11Pd")
        price_el = product.select_one("span.a8Pemb")
        link_el = product.select_one("a")
        source_el = product.select_one("div.aULzUe")

        if not (title_el and price_el and link_el):
            continue

        title = title_el.get_text(" ", strip=True)
        price = price_el.get_text(" ", strip=True)
        href = link_el.get("href")
        source = source_el.get_text(" ", strip=True) if source_el else _domain_for(href)

        listings.append(
            {
                "title": title,
                "price": price,
                "price_value": parse_price(price),
                "link": href,
                "source": source,
                "image": None,
                "in_stock": True,
                "stock_label": "Visit site",
            }
        )

        if len(listings) >= MAX_RESULTS:
            break

    return listings


def scrape_google_search(query: str) -> Iterable[Dict[str, object]]:
    """Perform a Google search and return lightweight results."""

    if not query.strip():
        return []

    html = safe_get(SEARCH_URL, params={"q": query, "hl": "en"}, timeout=4)
    if not html:
        logger.warning("Google search did not return HTML for query '%s'", query)
        return []

    organic = _parse_results(html)
    shopping = _parse_prices_from_shopping(html)

    combined: List[Dict[str, object]] = []
    combined.extend(shopping)
    combined.extend(organic)
    return combined[:MAX_RESULTS]
