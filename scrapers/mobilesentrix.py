
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .utils import safe_get, parse_price

BASE = "https://www.mobilesentrix.com"


def scrape_mobile_sentrix(query):
    search_url = f"{BASE}/search?q={query}"
    html = safe_get(search_url)
    soup = BeautifulSoup(html, "html.parser")
    link_tag = soup.select_one("a.product-item-link")
    if not link_tag:
        return []

    link = urljoin(BASE, link_tag.get("href", ""))
    title = link_tag.get_text(strip=True)

    prod_html = safe_get(link)
    prod_soup = BeautifulSoup(prod_html, "html.parser")
    price_tag = prod_soup.select_one("span.price")
    price = parse_price(price_tag.get_text()) if price_tag else 0.0
    in_stock = (
        prod_soup.find(string=lambda s: s and "out of stock" in s.lower()) is None
    )
    image_tag = prod_soup.select_one("img")
    image = (
        urljoin(BASE, image_tag["src"])
        if image_tag and image_tag.has_attr("src")
        else "https://via.placeholder.com/100"
    )

    return [
        {
            "title": title or query,
            "price": price,
            "in_stock": in_stock,
            "source": "MobileSentrix",
            "link": link,
            "image": image,
        }
    ]
=======

def scrape_mobilesentrix(query):
    return [{
        "title": "Mobilesentrix Result for '{}'".format(query),
        "price": 19.99,
        "in_stock": True,
        "source": "Mobilesentrix",
        "link": "https://mobilesentrix.com/search?q=" + query,
        "image": "https://via.placeholder.com/100"
    }]
