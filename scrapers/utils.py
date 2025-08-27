import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Use a full desktop browser header to avoid basic bot blocking
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/113.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def safe_get(url, params=None):
    """Fetch *url* and return the text body, or an empty string on failure."""
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return ""


def parse_price(text):
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text.replace(",", ""))
    return float(match.group(1)) if match else 0.0
