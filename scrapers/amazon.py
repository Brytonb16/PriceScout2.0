"""Amazon product search scraper."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .utils import parse_price, safe_get

logger = logging.getLogger(__name__)

BASE = "https://www.amazon.com"
SEARCH_URL = f"{BASE}/s"
MAX_RESULTS = 10


def _parse_results(html: str) -> List[Dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, object]] = []

    for card in soup.select("div[data-component-type='s-search-result']"):
        title_el = card.select_one("h2 a span")
        link_el = card.select_one("h2 a")
        price_el = card.select_one("span.a-offscreen") or card.select_one(
            "span.a-price > span.a-offscreen"
        )
        image_el = card.select_one("img.s-image")

        if not (title_el and link_el):
            continue

        title = title_el.get_text(" ", strip=True)
        link = urljoin(BASE, link_el.get("href", ""))
        price_raw = price_el.get_text(strip=True) if price_el else None
        price_value = parse_price(price_raw) if price_raw else None
        image = image_el.get("src") if image_el else None

        results.append(
            {
                "title": title,
                "link": link,
                "source": "Amazon",
                "price": price_raw,
                "price_value": price_value,
                "image": image,
                "in_stock": True,
                "stock_label": "View on Amazon",
            }
        )

        if len(results) >= MAX_RESULTS:
            break

    return results


def scrape_amazon(query: str) -> Iterable[Dict[str, object]]:
    if not query.strip():
        return []

    html = safe_get(SEARCH_URL, params={"k": query})
    if not html:
        logger.warning("Amazon search failed for query '%s'", query)
        return []

    parsed = _parse_results(html)
    if not parsed:
        logger.info("Amazon returned no parsable results for %s", query)

    return parsed
