import logging
import re
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from .utils import render_page, parse_price

BASE = "https://www.fixez.com"
logger = logging.getLogger(__name__)


def _matches_query(title: str, query: str) -> bool:
    """Return ``True`` when *title* is a reasonable match for *query*.

    At least half of the alphanumeric query tokens (minimum one) must appear in
    the product title to avoid flooding the results with unrelated listings.
    """

    tokens = [token for token in re.split(r"\W+", query.lower()) if len(token) >= 3]
    if not tokens:
        return True

    title_tokens = set(re.split(r"\W+", title.lower()))
    matches = sum(1 for token in tokens if token in title_tokens)
    required_matches = max(1, (len(tokens) + 1) // 2)

    return matches >= required_matches


def scrape_fixez(query):
    search_url = f"{BASE}/catalogsearch/result/?q={quote_plus(query)}"
    html = render_page(search_url, "li.product-item")
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("li.product-item, li.item.product.product-item") or soup.select(
        "div.product-item, div.item.product"
    )
    if not items:
        logger.warning("Fixez: no product items found for %s", query)
        return []

    results = []
    for item in items:
        link_tag = item.select_one("a.product-item-link") or item.select_one("a")
        price_tag = item.select_one("span.price") or item.select_one("span[data-price]")
        image_tag = item.select_one("img")
        if not link_tag:
            logger.warning("Fixez: missing link tag, skipping item")
            continue

        link = urljoin(BASE, link_tag.get("href", ""))
        title = link_tag.get_text(strip=True) or query
        if not _matches_query(title, query):
            continue
        raw_price = price_tag.get_text() if price_tag else None
        price = parse_price(raw_price) if raw_price else 0.0
        in_stock = item.find(string=lambda s: s and "out of stock" in s.lower()) is None
        image = (
            urljoin(BASE, image_tag["src"])
            if image_tag and image_tag.has_attr("src")
            else "https://via.placeholder.com/100"
        )

        results.append(
            {
                "title": title,
                "price": price,
                "in_stock": in_stock,
                "source": "Fixez",
                "link": link,
                "image": image,
            }
        )

    return results
