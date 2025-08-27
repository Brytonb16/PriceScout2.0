from urllib.parse import urljoin, quote_plus
from bs4 import BeautifulSoup
from .utils import safe_get, parse_price

BASE = "https://www.mengtor.com"


def scrape_mengtor(query):
    search_url = f"{BASE}/search?q={quote_plus(query)}"
    html = safe_get(search_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    item = soup.select_one("li.product-item")
    if not item:
        return []

    link_tag = item.select_one("a.product-item-link") or item.select_one("a")
    price_tag = item.select_one("span.price")
    image_tag = item.select_one("img")

    link = urljoin(BASE, link_tag.get("href", "")) if link_tag else search_url
    title = link_tag.get_text(strip=True) if link_tag else query

    price = parse_price(price_tag.get_text()) if price_tag else 0.0
    in_stock = item.find(string=lambda s: s and "out of stock" in s.lower()) is None
    image = (
        urljoin(BASE, image_tag["src"])
        if image_tag and image_tag.has_attr("src")
        else "https://via.placeholder.com/100"
    )

    prod_html = safe_get(link) if link_tag else None
    if prod_html:
        prod_soup = BeautifulSoup(prod_html, "html.parser")
        prod_price = prod_soup.select_one("span.price")
        if prod_price:
            price = parse_price(prod_price.get_text())
        in_stock = prod_soup.find(
            string=lambda s: s and "out of stock" in s.lower()
        ) is None
        prod_img = prod_soup.select_one("img")
        if prod_img and prod_img.has_attr("src"):
            image = urljoin(BASE, prod_img["src"])

    return [
        {
            "title": title,
            "price": price,
            "in_stock": in_stock,
            "source": "Mengtor",
            "link": link,
            "image": image,
        }
    ]
