import json
import pytest

from openai_search import _extract_json_array, _normalize_result, openai, search_openai


def test_search_openai(monkeypatch):
    def fake_create(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": "Here you go!\n" + json.dumps([
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


def test_extract_json_array_with_prose():
    text = "Some intro text." + json.dumps([{"title": "A"}]) + "Trailing"
    parsed = _extract_json_array(text)
    assert parsed == [{"title": "A"}]


@pytest.mark.parametrize(
    "item,expected",
    [
        (
            {"title": "A", "price": "12.5", "in_stock": 1, "source": "S", "link": "L", "image": "I"},
            {"title": "A", "price": 12.5, "in_stock": True, "source": "S", "link": "L", "image": "I"},
        ),
        (
            {},
            {
                "title": "Unknown Product",
                "price": 0.0,
                "in_stock": False,
                "source": "OpenAI",
                "link": "",
                "image": "",
            },
        ),
    ],
)
def test_normalize_result(item, expected):
    assert _normalize_result(item) == expected
