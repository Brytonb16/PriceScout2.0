import pytest

import search


@pytest.fixture(autouse=True)
def restore_scrapers(monkeypatch):
    original_sources = list(search.SCRAPER_SOURCES)
    yield
    monkeypatch.setattr(search, "SCRAPER_SOURCES", original_sources, raising=False)


def test_search_products_uses_scrapers_and_filters_with_match_threshold(monkeypatch):
    monkeypatch.setattr(
        search, "rewrite_query_with_vendors", lambda q: {"primary": q, "boosted": []}
    )

    sentinel: list[str] = []

    def fake_scraper_one(_query):
        sentinel.append("scraper-one")
        return [
            {"title": "iphone battery replacement", "price": 12, "source": "Store A", "link": "https://a/1"},
            {"title": "unrelated laptop bag", "price": 8, "source": "Store B", "link": "https://b/1"},
        ]

    def fake_scraper_two(_query):
        sentinel.append("scraper-two")
        return [{"title": "iphone battery replacement kit", "price": 15, "source": "Store C", "link": "https://c/1"}]

    monkeypatch.setattr(
        search,
        "SCRAPER_SOURCES",
        [("One", fake_scraper_one), ("Two", fake_scraper_two)],
    )

    monkeypatch.setattr(
        search, "summarize_offers_with_openai", lambda _q, offers: offers
    )

    results = search.search_products("iphone battery replacement")
    assert [item["title"] for item in results] == [
        "iphone battery replacement",
        "iphone battery replacement kit",
    ]
    assert sentinel == ["scraper-one", "scraper-two"]
    assert all(item["match_score"] >= 0.8 for item in results)


def test_search_products_returns_empty_for_unsupported_category(monkeypatch):
    monkeypatch.setattr(
        search, "rewrite_query_with_vendors", lambda q: {"primary": q, "boosted": []}
    )
    monkeypatch.setattr(
        search, "summarize_offers_with_openai", lambda _q, offers: offers
    )

    def fake_scraper(_query):
        return [{"title": "gaming mouse", "price": 10, "source": "Store", "link": "https://x/1"}]

    monkeypatch.setattr(search, "SCRAPER_SOURCES", [("Fake", fake_scraper)])

    assert search.search_products("gaming mouse") == []


def test_search_products_returns_empty_for_blank_query():
    assert search.search_products("   ") == []


def test_search_products_sorts_lowest_price_first(monkeypatch):
    monkeypatch.setattr(
        search, "rewrite_query_with_vendors", lambda q: {"primary": q, "boosted": []}
    )

    def fake_scraper(_query):
        return [
            {"title": "screen repair kit", "source": "Fixez", "price": 40, "link": "https://a/1"},
            {"title": "screen repair kit premium", "source": "Amazon", "price": 20, "link": "https://a/2"},
        ]

    monkeypatch.setattr(search, "SCRAPER_SOURCES", [("Fake", fake_scraper)])
    monkeypatch.setattr(search, "summarize_offers_with_openai", lambda _q, offers: offers)

    results = search.search_products("screen repair kit")
    assert [item["price"] for item in results] == [20, 40]


def test_search_products_falls_back_to_openai_when_scrapers_empty(monkeypatch):
    monkeypatch.setattr(
        search, "rewrite_query_with_vendors", lambda q: {"primary": q, "boosted": []}
    )
    monkeypatch.setattr(search, "SCRAPER_SOURCES", [("Empty", lambda _q: [])])
    monkeypatch.setattr(
        search,
        "search_openai",
        lambda _q: [
            {
                "title": "iphone battery replacement",
                "price": 19,
                "source": "OpenAI",
                "link": "https://example.com/offer",
            }
        ],
    )
    monkeypatch.setattr(search, "summarize_offers_with_openai", lambda _q, offers: offers)

    results = search.search_products("iphone battery replacement")
    assert len(results) == 1
    assert results[0]["source"] == "OpenAI"
