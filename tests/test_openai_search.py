import json
import openai
from openai_search import (
    rewrite_query_with_vendors,
    search_openai,
    summarize_offers_with_openai,
)


def test_search_openai(monkeypatch):
    def fake_create(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps([
                            {
                                "title": "Item One",
                                "price": 1.0,
                                "in_stock": True,
                                "source": "AI",
                                "link": "http://example.com",
                                "image": "http://example.com/img.jpg",
                            }
                        ])
                    }
                }
            ]
        }

    monkeypatch.setattr(openai.ChatCompletion, "create", fake_create)
    results = search_openai("screen")
    assert len(results) == 1
    first = results[0]
    assert first["title"] == "Item One"
    assert first["price"] == 1.0
    assert first["in_stock"] is True
    assert first["source"] == "AI"


def test_rewrite_query_with_vendors_fallback(monkeypatch):
    monkeypatch.setattr(openai.ChatCompletion, "create", lambda **kwargs: (_ for _ in ()).throw(Exception()))
    rewritten = rewrite_query_with_vendors("iphone screen")
    assert rewritten["primary"] == "iphone screen"
    assert any("MobileSentrix" in q for q in rewritten["boosted"])


def test_summarize_offers_with_openai_guarantees_vendors(monkeypatch):
    monkeypatch.setattr(openai.ChatCompletion, "create", lambda **kwargs: (_ for _ in ()).throw(Exception()))

    offers = [
        {"title": "Generic", "source": "Other", "price": 20},
        {"title": "MSX", "source": "MobileSentrix", "price": 25},
        {"title": "Amazon Deal", "source": "Amazon", "price": 30},
        {"title": "eBay", "source": "eBay", "price": 40},
        {"title": "Fixez Part", "source": "Fixez", "price": 35},
    ]

    summarized = summarize_offers_with_openai("screen", offers)
    sources = [item.get("source") for item in summarized[:4]]
    assert "MobileSentrix" in sources
    assert "Fixez" in sources
    assert "Amazon" in sources
    assert any("ebay" in str(src).lower() for src in sources)
