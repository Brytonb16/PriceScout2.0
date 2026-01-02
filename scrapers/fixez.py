import logging
import math
import re
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from .utils import parse_price, render_page

BASE = "https://www.fixez.com"
logger = logging.getLogger(__name__)


def _normalize_tokens(text: str) -> set[str]:
    """Tokenize *text* into normalized words for fuzzy matching.

    Tokens shorter than three characters are ignored. For plural words we also
    add a singular variant to improve matching between query and title.
    """

    tokens: set[str] = set()
    for token in re.split(r"\W+", text.lower()):
        if len(token) < 3:
            continue

        tokens.add(token)

        if token.endswith("es") and len(token) > 4:
            tokens.add(token[:-2])
        elif token.endswith("s") and len(token) > 3:
            tokens.add(token[:-1])

    return tokens


def _matches_query(title: str, query: str) -> bool:
    """Return ``True`` when *title* closely matches *query*.

    At least ~70% of the query tokens (minimum one) must appear in the product
    title. This keeps results relevant for multi-word searches such as console
    accessory kits while staying resilient to pluralization differences.
    """

    tokens = _normalize_tokens(query)
    if not tokens:
        return True

    title_tokens = _normalize_tokens(title)

    # Require longer/more distinctive tokens to be present to avoid loosely
    # related accessories (e.g., power boards for a power supply search).
    mandatory_tokens = {token for token in tokens if len(token) >= 6}
    if mandatory_tokens and not mandatory_tokens.issubset(title_tokens):
        return False

    matches = sum(1 for token in tokens if token in title_tokens)
    required_matches = max(1, math.ceil(len(tokens) * 0.8))

    if matches >= required_matches:
        return True

    similarity = matches / len(tokens)
    return similarity >= 0.85


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
