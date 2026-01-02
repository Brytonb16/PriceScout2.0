"""Curated offline catalog for predictable demo searches."""
from __future__ import annotations

from typing import Dict, Iterable, List

CatalogItem = Dict[str, object]

# A small, representative catalog so local searches work without network access.
# Prices are expressed as strings for parity with scraped results but we keep an
# explicit numeric ``price_value`` to simplify sorting downstream.
CATALOG: List[CatalogItem] = [
    {
        "title": "iPhone 12 OLED Screen Replacement Kit",
        "price": "$129.99",
        "price_value": 129.99,
        "in_stock": True,
        "source": "Demo Mobile Parts",
        "link": "https://demo.local/iphone-12-screen",
        "image": "https://demo.local/img/iphone-12-screen.jpg",
        "stock_label": "Ships today",
        "keywords": "cell phone display glass digitizer",  # assists keyword matching
    },
    {
        "title": "Samsung Galaxy S21 Charging Port Flex Cable",
        "price": "$18.50",
        "price_value": 18.50,
        "in_stock": True,
        "source": "Demo Mobile Parts",
        "link": "https://demo.local/galaxy-s21-charge-port",
        "image": "https://demo.local/img/galaxy-s21-charge-port.jpg",
        "stock_label": "In stock",
        "keywords": "cell phone usb-c dock connector",  # assists keyword matching
    },
    {
        "title": "MacBook Pro 2019 16\" Replacement Keyboard (US)",
        "price": "$179.00",
        "price_value": 179.00,
        "in_stock": True,
        "source": "Demo Laptop Parts",
        "link": "https://demo.local/mbp-2019-keyboard",
        "image": "https://demo.local/img/mbp-2019-keyboard.jpg",
        "stock_label": "Genuine part",
        "keywords": "laptop topcase keyboard",  # assists keyword matching
    },
    {
        "title": "Dell XPS 13 7390 52Wh Battery (GPM03)",
        "price": "$89.95",
        "price_value": 89.95,
        "in_stock": True,
        "source": "Demo Laptop Parts",
        "link": "https://demo.local/xps-13-7390-battery",
        "image": "https://demo.local/img/xps-13-7390-battery.jpg",
        "stock_label": "1-year warranty",
        "keywords": "ultrabook battery pack",
    },
    {
        "title": "HP Pavilion 15.6"" FHD LCD Screen Replacement",
        "price": "$64.99",
        "price_value": 64.99,
        "in_stock": True,
        "source": "Demo Laptop Parts",
        "link": "https://demo.local/hp-pavilion-15-lcd",
        "image": "https://demo.local/img/hp-pavilion-15-lcd.jpg",
        "stock_label": "Matte display",
        "keywords": "laptop display panel lcd",
    },
    {
        "title": "Lenovo ThinkPad T480 Palmrest with Touchpad",
        "price": "$54.25",
        "price_value": 54.25,
        "in_stock": True,
        "source": "Demo Laptop Parts",
        "link": "https://demo.local/t480-palmrest",
        "image": "https://demo.local/img/t480-palmrest.jpg",
        "stock_label": "Original OEM",
        "keywords": "laptop chassis top cover",
    },
    {
        "title": "Nintendo Switch Internal Cooling Fan",
        "price": "$21.75",
        "price_value": 21.75,
        "in_stock": True,
        "source": "Demo Console Parts",
        "link": "https://demo.local/switch-fan",
        "image": "https://demo.local/img/switch-fan.jpg",
        "stock_label": "Quiet version",
        "keywords": "console replacement fan",
    },
    {
        "title": "PlayStation 5 HDMI Port Replacement",
        "price": "$14.99",
        "price_value": 14.99,
        "in_stock": True,
        "source": "Demo Console Parts",
        "link": "https://demo.local/ps5-hdmi",
        "image": "https://demo.local/img/ps5-hdmi.jpg",
        "stock_label": "Bulk pack",
        "keywords": "game console port socket",
    },
    {
        "title": "Xbox Series X Power Supply Unit",
        "price": "$94.00",
        "price_value": 94.00,
        "in_stock": True,
        "source": "Demo Console Parts",
        "link": "https://demo.local/xbox-series-x-psu",
        "image": "https://demo.local/img/xbox-series-x-psu.jpg",
        "stock_label": "Refurbished",
        "keywords": "console power supply",  # assists keyword matching
    },
    {
        "title": "GeForce RTX 3070 Dual Cooling Fan Set",
        "price": "$27.95",
        "price_value": 27.95,
        "in_stock": True,
        "source": "Demo PC Parts",
        "link": "https://demo.local/rtx-3070-fans",
        "image": "https://demo.local/img/rtx-3070-fans.jpg",
        "stock_label": "Pair with screws",
        "keywords": "graphics card cooler gpu",
    },
]


_DEFAULT_RETURN_LIMIT = 10


def _match_score(query: str, text: str) -> int:
    tokens = [token for token in query.lower().split() if len(token) > 2]
    haystack = text.lower()
    return sum(token in haystack for token in tokens)


def scrape_local_catalog(query: str, limit: int = _DEFAULT_RETURN_LIMIT) -> Iterable[CatalogItem]:
    """Return catalog items that loosely match ``query``.

    This keeps the app useful when network scrapers cannot run (for example in
    CI or restricted environments). Items are scored by keyword overlap and
    returned with the best matches first.
    """

    if not query.strip():
        return []

    scored: list[tuple[int, CatalogItem]] = []
    for item in CATALOG:
        text = f"{item['title']} {item.get('keywords', '')}"
        score = _match_score(query, text)
        if score:
            scored.append((score, item))

    scored.sort(key=lambda pair: (-pair[0], pair[1]["price_value"]))
    return [dict(entry) for _, entry in scored[:limit]]
