import time

import pytest

import search


@pytest.fixture(autouse=True)
def restore_scrapers(monkeypatch):
    original_sources = list(search.SCRAPER_SOURCES)
    yield
    monkeypatch.setattr(search, "SCRAPER_SOURCES", original_sources, raising=False)


def test_search_products_prefers_openai(monkeypatch):
    monkeypatch.setattr(
        search, "rewrite_query_with_vendors", lambda q: {"primary": q, "boosted": []}
    )

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

    monkeypatch.setattr(
        search, "summarize_offers_with_openai", lambda _q, offers: offers
    )

    results = search.search_products("battery")
    assert results == [{"title": "Scraper 1"}, {"title": "Scraper 2"}]
    assert sentinel == ["scraper-one", "scraper-two"]


def test_search_products_falls_back_to_scrapers(monkeypatch):
    monkeypatch.setattr(
        search, "rewrite_query_with_vendors", lambda q: {"primary": q, "boosted": []}
    )
    monkeypatch.setattr(
        search, "summarize_offers_with_openai", lambda _q, offers: offers
    )

    def fake_scraper(_query):
        return [{"title": "Scraper"}]

    monkeypatch.setattr(search, "SCRAPER_SOURCES", [("Fake", fake_scraper)])

    results = search.search_products("screen")
    assert results == [{"title": "Scraper"}]


def test_search_products_returns_empty_for_blank_query():
    assert search.search_products("   ") == []


def test_search_products_prioritizes_required_vendors(monkeypatch):
    monkeypatch.setattr(
        search, "rewrite_query_with_vendors", lambda q: {"primary": q, "boosted": []}
    )

    def fake_scraper(_query):
        return [
            {"title": "Generic", "source": "Other", "price": 20},
            {"title": "MSX", "source": "MobileSentrix", "price": 25},
            {"title": "Amazon Deal", "source": "Amazon", "price": 30},
            {"title": "eBay", "source": "eBay", "price": 40},
            {"title": "Fixez Part", "source": "Fixez", "price": 35},
        ]

    monkeypatch.setattr(search, "SCRAPER_SOURCES", [("Fake", fake_scraper)])
    results = search.search_products("screen")

    sources = [item.get("source") for item in results[:4]]
    assert "MobileSentrix" in sources
    assert "Fixez" in sources
    assert "Amazon" in sources
    assert any("ebay" in str(src).lower() for src in sources)


def test_search_limits_query_variants(monkeypatch):
    monkeypatch.setattr(search, "MAX_QUERY_VARIANTS", 2)
    monkeypatch.setattr(search, "MAX_SEARCH_SECONDS", 5.0)

    monkeypatch.setattr(search, "summarize_offers_with_openai", lambda _q, offers: offers)
    monkeypatch.setattr(
        search,
        "rewrite_query_with_vendors",
        lambda q: {"primary": q, "boosted": [f"{q} msx", f"{q} amazon", f"{q} ebay"]},
    )

    queries_seen: list[str] = []

    def fake_scraper(query: str):
        queries_seen.append(query)
        return []

    monkeypatch.setattr(search, "SCRAPER_SOURCES", [("Fake", fake_scraper)])

    search.search_products("screen")

    assert queries_seen == ["screen", "screen msx"]


def test_search_respects_time_budget(monkeypatch):
    monkeypatch.setattr(search, "MAX_QUERY_VARIANTS", 5)
    monkeypatch.setattr(search, "MAX_SEARCH_SECONDS", 0.01)

    monkeypatch.setattr(search, "summarize_offers_with_openai", lambda _q, offers: offers)
    monkeypatch.setattr(
        search,
        "rewrite_query_with_vendors",
        lambda q: {"primary": q, "boosted": [f"{q} one", f"{q} two"]},
    )

    def slow_scraper(query: str):
        time.sleep(0.02)
        return [{"title": query}]

    monkeypatch.setattr(search, "SCRAPER_SOURCES", [("Slow", slow_scraper)])

    results = search.search_products("battery")

    assert results == [{"title": "battery"}]

