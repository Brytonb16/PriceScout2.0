import pytest

import search


@pytest.fixture(autouse=True)
def restore_scrapers(monkeypatch):
    original_sources = list(search.SCRAPER_SOURCES)
    yield
    monkeypatch.setattr(search, "SCRAPER_SOURCES", original_sources, raising=False)


def test_search_products_prefers_openai(monkeypatch):
    sentinel: list[str] = []

    def fake_scraper_one(_query):
        sentinel.append("scraper-one")
        return [{"title": "Scraper 1"}]

    def fake_scraper_two(_query):
        sentinel.append("scraper-two")
        return [{"title": "Scraper 2"}]

    monkeypatch.setattr(
        search,
        "SCRAPER_SOURCES",
        [("One", fake_scraper_one), ("Two", fake_scraper_two)],
    )

    results = search.search_products("battery")
    assert results == [{"title": "Scraper 1"}, {"title": "Scraper 2"}]
    assert sentinel == ["scraper-one", "scraper-two"]


def test_search_products_falls_back_to_scrapers(monkeypatch):
    def fake_scraper(_query):
        return [{"title": "Scraper"}]

    monkeypatch.setattr(search, "SCRAPER_SOURCES", [("Fake", fake_scraper)])

    results = search.search_products("screen")
    assert results == [{"title": "Scraper"}]


def test_search_products_returns_empty_for_blank_query():
    assert search.search_products("   ") == []

