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
    """Extract a numeric price from *text*.

    Common lead-in phrases such as "From" or "Starting at" are stripped
    before parsing. When a price range like "$10-$20" is supplied, the
    average of the bounds is returned. If no numbers can be found, ``0.0`` is
    returned.
    """

    # Remove helpful but non-numeric phrases
    normalized = re.sub(r"\b(from|starting at)\b", "", text, flags=re.I)

    # Normalise dash types and remove thousands separators
    normalized = normalized.replace("–", "-").replace(",", "")

    # Find all numbers in the string
    numbers = re.findall(r"([0-9]+(?:\.[0-9]+)?)", normalized)
    if not numbers:
        return 0.0

    # If a range is detected, return the average of the first two numbers
    if "-" in normalized and len(numbers) >= 2:
        values = [float(n) for n in numbers[:2]]
        return sum(values) / len(values)

    return float(numbers[0])
