import json
import openai
from openai_search import search_openai


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
