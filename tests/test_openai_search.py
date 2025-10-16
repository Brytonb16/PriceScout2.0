import json
import pytest

import openai_search
from openai_search import _coerce_array, _extract_json_array, _normalize_result, search_openai


def test_search_openai(monkeypatch):
    payload = json.dumps(
        [
            {
                "title": "Item One",
                "price": 1.0,
                "in_stock": True,
                "source": "AI",
                "link": "http://example.com",
                "image": "http://example.com/img.jpg",
            }
        ]
    )

    monkeypatch.setattr(openai_search, "_invoke_openai", lambda _messages: "Here you go!\n" + payload)

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


def test_extract_json_array_from_object():
    text = json.dumps({"results": [{"title": "B"}]})
    parsed = _extract_json_array(text)
    assert parsed == [{"title": "B"}]


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


def test_coerce_array_filters_non_dict_entries():
    data = ["a", {"title": "A"}]
    assert _coerce_array(data) == [{"title": "A"}]
