import pytest
import scrapers.utils as utils
import playwright.sync_api as playwright_sync

from scrapers.utils import parse_price

def test_parse_price_single():
    assert parse_price("Starting at $1,234.50") == pytest.approx(1234.50)

def test_parse_price_range():
    assert parse_price("$10–$20") == pytest.approx(15.0)

def test_parse_price_malformed():
    assert parse_price("Free") == 0.0


def test_render_page_fallback(monkeypatch):
    """If Playwright fails, render_page should fall back to safe_get."""

    def fake_sync_playwright():
        class Dummy:
            def __enter__(self):
                raise RuntimeError("boom")

            def __exit__(self, exc_type, exc, tb):
                pass

        return Dummy()

    monkeypatch.setattr(playwright_sync, "sync_playwright", fake_sync_playwright)
    monkeypatch.setattr(utils, "safe_get", lambda url, params=None: "<html>fallback</html>")

    assert utils.render_page("https://example.com") == "<html>fallback</html>"
