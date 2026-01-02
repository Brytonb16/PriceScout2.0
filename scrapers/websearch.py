"""Web search scraper used as a lightweight fallback."""

from __future__ import annotations

import logging
import re
from typing import Dict, Iterable, List
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup

from scrapers.utils import parse_price, safe_get

logger = logging.getLogger(__name__)

SEARCH_URL = "https://duckduckgo.com/html/"
MAX_RESULTS = 10
MAX_PREVIEW_FETCHES = 5
PRIORITY_PREVIEW_DOMAINS = (
    "amazon.com",
    "www.amazon.com",
    "smile.amazon.com",
    "ebay.com",
    "www.ebay.com",
    "ebay.co.uk",
    "www.ebay.co.uk",
    "ebay.ca",
    "www.ebay.ca",
    "mobilesentrix.com",
)


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


def _extract_price_text(soup: BeautifulSoup, domain: str) -> str | None:
    """Return a price string for the given ``domain`` if present."""

    domain = domain.lower()

    def find_by_selectors(selectors):
        for selector in selectors:
            tag = soup.select_one(selector)
            if not tag:
                continue
            value = (
                tag.get("content")
                or tag.get("value")
                or tag.get_text(strip=True)
                or tag.get("aria-label")
            )
            if value and re.search(r"\d", value):
                return value.strip()
        return None

    common_price_selectors = [
        "meta[property='product:price:amount']",
        "meta[property='og:price:amount']",
        "meta[name='price']",
        "meta[itemprop='price']",
        "span.price",
        "span[data-price]",
        "meta[name='twitter:data1']",
    ]

    amazon_selectors = [
        "span.a-offscreen",
        "span#priceblock_ourprice",
        "span#priceblock_dealprice",
        "span#priceblock_saleprice",
        "span.a-price > span.a-offscreen",
        "span.a-price-whole",
    ]

    ebay_selectors = [
        "span[itemprop='price']",
        "span#prcIsum",
        "span#mm-saleDscPrc",
        "span#prcIsum_bidPrice",
        "span.s-item__price",
    ]

    domain_specific = []
    if "amazon." in domain:
        domain_specific = amazon_selectors
    elif "ebay." in domain:
        domain_specific = ebay_selectors
    elif "mobilesentrix" in domain:
        # Occasionally MobileSentrix pages are encountered via web search as well
        domain_specific = ["span.price", "span[data-price]"]

    return find_by_selectors(domain_specific or common_price_selectors) or find_by_selectors(
        common_price_selectors
    )


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

    domain = urlparse(url).netloc
    raw_price = _extract_price_text(soup, domain)
    if raw_price:
        details["price"] = raw_price
        details["price_value"] = parse_price(raw_price)

    if "price" not in details:
        text = soup.get_text(" ", strip=True)
        match = re.search(r"\$\s*([0-9]+(?:\.[0-9]+)?)", text)
        if match:
            raw_price = match.group(0)
            details["price"] = raw_price
            details["price_value"] = parse_price(raw_price)

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

    for index, item in enumerate(results):
        domain = item.get("source", "").lower()
        should_preview = index < MAX_PREVIEW_FETCHES or any(
            domain.endswith(prioritized) for prioritized in PRIORITY_PREVIEW_DOMAINS
        )
        if not should_preview:
            continue

        preview = _preview_details_for(item["link"])

        if preview.get("image") and not item.get("image"):
            item["image"] = preview["image"]

        if preview.get("price") and not item.get("price"):
            item["price"] = preview["price"]
            if preview.get("price_value") is not None:
                item["price_value"] = preview["price_value"]

    return results
