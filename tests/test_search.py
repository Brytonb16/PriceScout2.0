import pytest

import search


@pytest.fixture(autouse=True)
def restore_scrapers(monkeypatch):
    original_sources = list(search.SCRAPER_SOURCES)
    yield
    monkeypatch.setattr(search, "SCRAPER_SOURCES", original_sources, raising=False)


def test_search_products_prefers_openai(monkeypatch):
    monkeypatch.setattr(search, "search_openai", lambda q: [{"title": "AI"}])

    sentinel = []

    def fake_scraper(_query):
        sentinel.append("scraper-called")
        return [{"title": "Scraper"}]

    monkeypatch.setattr(search, "SCRAPER_SOURCES", [("Fake", fake_scraper)])

    results = search.search_products("battery")
    assert results == [{"title": "AI"}]
    assert not sentinel


def test_search_products_falls_back_to_scrapers(monkeypatch):
    monkeypatch.setattr(search, "search_openai", lambda q: [])

    def fake_scraper(_query):
        return [{"title": "Scraper"}]

    monkeypatch.setattr(search, "SCRAPER_SOURCES", [("Fake", fake_scraper)])

    results = search.search_products("screen")
    assert results == [{"title": "Scraper"}]

