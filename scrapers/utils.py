import logging
import re
import requests

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
logger = logging.getLogger(__name__)


def safe_get(url, params=None, *, timeout: int | float = 10):
    """Fetch *url* and return the text body, or ``None`` on failure.

    A configurable ``timeout`` keeps flaky endpoints from slowing down the
    overall search request. Individual scrapers can lower the default when
    reaching out to brittle providers like Google Search so failures fail
    fast instead of blocking the whole response cycle.
    """
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception:
        logger.exception("Request failed for %s", url)
        return None


def render_page(url, wait_selector=None):
    """Use Playwright to render *url* and return the HTML content.

    If ``wait_selector`` is provided, the function waits for the selector to
    appear before returning the page content. If Playwright is unavailable or
    rendering fails, the function falls back to a static fetch via
    :func:`safe_get` and returns that HTML instead of ``None``.
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=15000)
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=5000)
                except Exception:
                    logger.warning("Selector %s not found for %s", wait_selector, url)
            content = page.content()
            browser.close()
            return content
    except Exception:
        logger.exception("Playwright failed for %s", url)
        logger.info("Falling back to static fetch for %s", url)
        return safe_get(url)


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
