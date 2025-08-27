import logging
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from .utils import render_page, parse_price

BASE = "https://www.mengtor.com"
logger = logging.getLogger(__name__)


def scrape_mengtor(query):
    search_url = f"{BASE}/search?q={quote_plus(query)}"
    html = render_page(search_url, "li.product-item")
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("li.product-item") or soup.select("div.product-item")
    if not items:
        logger.warning("Mengtor: no product items found for %s", query)
        return []

    results = []
    for item in items:
        link_tag = item.select_one("a.product-item-link") or item.select_one("a")
        price_tag = item.select_one("span.price")
        image_tag = item.select_one("img")
        if not link_tag:
            logger.warning("Mengtor: missing link tag, skipping item")
            continue

        link = urljoin(BASE, link_tag.get("href", ""))
        title = link_tag.get_text(strip=True) or query
        price = parse_price(price_tag.get_text()) if price_tag else 0.0
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
                "source": "Mengtor",
                "link": link,
                "image": image,
            }
        )

    return results
