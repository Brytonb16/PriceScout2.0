import json
import types

import pytest

import openai_search
from openai_search import (
    _coerce_array,
    _extract_json_array,
    _normalize_result,
    search_openai,
)


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


def test_search_openai_reformat_attempt(monkeypatch):
    payload = json.dumps(
        [
            {
                "title": "Reformatted",
                "price": 5.5,
                "in_stock": True,
                "source": "AI",
                "link": "http://example.com/reformatted",
                "image": "http://example.com/reformatted.jpg",
            }
        ]
    )

    calls = []

    def fake_invoke(messages):
        calls.append(messages[-1]["content"])
        if len(calls) == 1:
            return "1. Product A - $5.50 - example.com"
        return payload

    monkeypatch.setattr(openai_search, "_invoke_openai", fake_invoke)

    results = search_openai("battery")

    assert len(results) == 1
    assert results[0]["title"] == "Reformatted"
    assert "Reformat" in calls[1]


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
            {
                "title": "B",
                "price": "$1,299.99 USD",
                "in_stock": "true",
                "source": "",
                "link": None,
                "image": None,
            },
            {
                "title": "B",
                "price": 1299.99,
                "in_stock": True,
                "source": "OpenAI",
                "link": "",
                "image": "",
            },
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


def test_legacy_model_fallback(monkeypatch):
    payload = json.dumps(
        [
            {
                "title": "Fallback Item",
                "price": 12.5,
                "in_stock": True,
                "source": "AI",
                "link": "http://example.com/fallback",
                "image": "http://example.com/fallback.jpg",
            }
        ]
    )

    calls = []

    class StubChatCompletion:
        @staticmethod
        def create(*_args, **kwargs):
            model = kwargs.get("model")
            calls.append(model)
            if model != "gpt-3.5-turbo":
                raise RuntimeError("The model does not exist")
            return {"choices": [{"message": {"content": payload}}]}

    stub_openai = types.SimpleNamespace(ChatCompletion=StubChatCompletion)

    monkeypatch.setattr(openai_search, "openai", stub_openai)
    monkeypatch.setattr(openai_search, "_client", None)

    results = search_openai("screen")

    assert len(results) == 1
    assert results[0]["title"] == "Fallback Item"
    assert calls[0] == openai_search.MODEL
    assert "gpt-3.5-turbo" in calls
