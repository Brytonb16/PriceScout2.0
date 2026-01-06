"""Ebay product search scraper."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from .utils import parse_price, render_page

logger = logging.getLogger(__name__)

BASE = "https://www.ebay.com"
SEARCH_URL = f"{BASE}/sch/i.html"
MAX_RESULTS = 10


def _parse_results(html: str) -> List[Dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, object]] = []

    for card in soup.select("li.s-item"):
        title_el = card.select_one("h3.s-item__title")
        link_el = card.select_one("a.s-item__link")
        price_el = card.select_one("span.s-item__price")
        image_el = card.select_one("img.s-item__image-img")

        if not (title_el and link_el and price_el):
            continue

        title = title_el.get_text(" ", strip=True)
        link = link_el.get("href", "")
        price_raw = price_el.get_text(" ", strip=True)
        price_value = parse_price(price_raw)
        image = image_el.get("src") if image_el else None

        results.append(
            {
                "title": title,
                "link": urljoin(BASE, link),
                "source": "Ebay",
                "price": price_raw,
                "price_value": price_value,
                "image": image,
                "in_stock": True,
                "stock_label": "View on Ebay",
            }
        )

        if len(results) >= MAX_RESULTS:
            break

    return results


def scrape_ebay(query: str) -> Iterable[Dict[str, object]]:
    if not query.strip():
        return []

    url = f"{SEARCH_URL}?{urlencode({'_nkw': query})}"
    html = render_page(url, wait_selector="li.s-item")
    if not html:
        logger.warning("Ebay search failed for query '%s'", query)
        return []

    parsed = _parse_results(html)
    if not parsed:
        logger.info("Ebay returned no parsable results for %s", query)

    return parsed
