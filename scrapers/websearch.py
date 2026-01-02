"""Web search scraper used as a lightweight fallback."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup

from scrapers.utils import parse_price, safe_get

logger = logging.getLogger(__name__)

SEARCH_URL = "https://duckduckgo.com/html/"
MAX_RESULTS = 10
MAX_PREVIEW_FETCHES = 5


def _domain_for(url: str) -> str:
    try:
        parsed = urlparse(url)
        return parsed.netloc or "Web"
    except Exception:  # pragma: no cover - defensive
        return "Web"


def _resolve_link(href: str) -> str:
    """Return the destination URL for DuckDuckGo redirect links."""

    if not href:
        return ""

    try:
        parsed = urlparse(href)
    except Exception:  # pragma: no cover - defensive
        return href

    # DuckDuckGo wraps outbound links with /l/?uddg=<encoded>
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        try:
            params = parse_qs(parsed.query)
            target = params.get("uddg", [href])[0]
            return unquote(target)
        except Exception:  # pragma: no cover - defensive
            return href

    return href


def _preview_details_for(url: str) -> Dict[str, object]:
    """Fetch lightweight preview details such as image and price for ``url``."""

    html = safe_get(url)
    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    details: Dict[str, object] = {}

    image_selectors = [
        "meta[property='og:image']",
        "meta[name='og:image']",
        "meta[name='twitter:image']",
        "meta[property='twitter:image']",
        "link[rel='image_src']",
    ]

    for selector in image_selectors:
        tag = soup.select_one(selector)
        if tag:
            content = tag.get("content") or tag.get("href")
            if content:
                details["image"] = content
                break

    price_selectors = [
        "meta[property='product:price:amount']",
        "meta[property='og:price:amount']",
        "meta[name='price']",
        "meta[itemprop='price']",
    ]

    for selector in price_selectors:
        tag = soup.select_one(selector)
        if tag:
            raw_price = tag.get("content") or tag.get("value")
            if raw_price:
                details["price"] = raw_price.strip()
                price_value = parse_price(raw_price)
                if price_value:
                    details["price_value"] = price_value
                break

    return details


def _preview_image_for(url: str) -> str | None:
    """Return only the preview image URL for ``url`` for backward-compatibility."""

    details = _preview_details_for(url)
    image = details.get("image")
    return str(image) if image else None


def _is_repair_guide(title: str, snippet: str | None) -> bool:
    text = f"{title} {snippet or ''}".lower()
    guide_indicators = (
        "repair guide",
        "ifixit",
        "how to",
        "tutorial",
        "step-by-step",
    )
    return any(indicator in text for indicator in guide_indicators)


def _parse_results(html: str, query: str) -> List[Dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, object]] = []
    allow_guides = "guide" in query.lower()

    for block in soup.select("div.result"):
        link_el = block.select_one("a.result__a")
        if not link_el:
            continue

        href = _resolve_link(link_el.get("href"))
        source = _domain_for(href)
        if not href or source.endswith("duckduckgo.com"):
            continue

        title = link_el.get_text(" ", strip=True)
        snippet_el = block.select_one("div.result__snippet") or block.select_one(
            "a.result__snippet"
        )
        snippet = snippet_el.get_text(" ", strip=True) if snippet_el else None

        if not allow_guides and _is_repair_guide(title, snippet):
            continue

        results.append(
            {
                "title": title,
                "link": href,
                "source": source,
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

    results = _parse_results(html, query)

    for item in results[:MAX_PREVIEW_FETCHES]:
        preview = _preview_details_for(item["link"])

        if preview.get("image") and not item.get("image"):
            item["image"] = preview["image"]

        if preview.get("price") and not item.get("price"):
            item["price"] = preview["price"]
            if preview.get("price_value") is not None:
                item["price_value"] = preview["price_value"]

    return results
