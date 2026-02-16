import pytest
import scrapers.utils as utils
import playwright.sync_api as playwright_sync
from requests.exceptions import ProxyError

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


def test_safe_get_retries_without_proxy(monkeypatch):
    class DummyResponse:
        text = "<html>ok</html>"

        def raise_for_status(self):
            return None

    def fake_requests_get(*_args, **_kwargs):
        raise ProxyError("proxy blocked")

    class DummySession:
        def __init__(self):
            self.trust_env = True

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, *_args, **_kwargs):
            assert self.trust_env is False
            return DummyResponse()

    monkeypatch.setattr(utils.requests, "get", fake_requests_get)
    monkeypatch.setattr(utils.requests, "Session", DummySession)

    assert utils.safe_get("https://example.com") == "<html>ok</html>"
