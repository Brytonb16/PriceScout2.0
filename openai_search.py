"""Utilities for performing OpenAI-backed product searches."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Union

logger = logging.getLogger(__name__)

try:  # pragma: no cover - exercised when the modern SDK is installed
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - exercised in CI when openai absent
    OpenAI = None  # type: ignore

try:
    import openai as _legacy_openai  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised in CI environment
    _legacy_openai = None  # type: ignore


class _MissingOpenAI:  # pragma: no cover - defensive fallback for CI
    class ChatCompletion:  # pylint: disable=too-few-public-methods
        @staticmethod
        def create(*_args, **_kwargs):
            raise RuntimeError("The 'openai' package is required to run searches.")


openai = _legacy_openai or _MissingOpenAI()  # Re-export for the test suite

API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

_client: Optional[OpenAI] = None
if OpenAI is not None:  # pragma: no branch - simple guard for optional dependency
    try:
        _client = OpenAI(api_key=API_KEY)
    except Exception:  # pragma: no cover - instantiation failure should not crash
        logger.exception("Unable to initialise OpenAI client")
        _client = None

if hasattr(openai, "api_key"):
    openai.api_key = API_KEY

PROMPT_TEMPLATE = """
Return ONLY a valid JSON array (no markdown, no commentary) describing at least
five relevant products for the search query "{query}". Each product must be an
object containing: title (string), price (number), in_stock (boolean), source
(string), link (string URL), and image (string URL). If exact data is unknown,
provide your best estimate and set in_stock to false. Make sure prices are
numeric values (floats) without currency symbols.
""".strip()

JSON_ARRAY_PATTERN = re.compile(r"\[\s*\{.*\}\s*\]", re.DOTALL)
PREFERRED_OBJECT_KEYS = ("products", "results", "items", "data")


def _first_text_chunk(response: Any) -> str:
    """Extract the primary text payload from an OpenAI SDK response."""

    if not response:
        return ""

    # Modern responses API
    text = getattr(response, "output_text", None)
    if text:
        return text

    output: Iterable[Any] = getattr(response, "output", []) or []
    parts: List[str] = []
    for block in output:
        content = getattr(block, "content", []) or []
        for item in content:
            text_value = getattr(item, "text", None)
            if not text_value:
                continue
            value = getattr(text_value, "value", None)
            if value:
                parts.append(value)
    if parts:
        return "".join(parts)

    # ChatCompletion style response
    choices: Iterable[Any] = getattr(response, "choices", []) or []
    for choice in choices:
        message = getattr(choice, "message", None) or {}
        content = message.get("content") if isinstance(message, dict) else getattr(message, "content", "")
        if content:
            return content
    return ""


def _invoke_openai(messages: List[Dict[str, str]]) -> str:
    """Call whichever OpenAI client is available and return the raw text."""

    # Prefer the modern client when available.
    if _client is not None:
        try:
            response = _client.chat.completions.create(  # type: ignore[attr-defined]
                model=MODEL,
                temperature=0.2,
                messages=messages,
            )
            text = _first_text_chunk(response)
            if text:
                return text
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("OpenAI chat.completions call failed")

        try:
            rich_messages = [
                {
                    "role": msg["role"],
                    "content": [{"type": "text", "text": msg["content"]}],
                }
                for msg in messages
            ]
            response = _client.responses.create(  # type: ignore[attr-defined]
                model=MODEL,
                temperature=0.2,
                input=rich_messages,
            )
            text = _first_text_chunk(response)
            if text:
                return text
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("OpenAI responses call failed")

    # Fall back to the legacy global module if present.
    if hasattr(openai, "ChatCompletion"):
        try:
            response = openai.ChatCompletion.create(  # type: ignore[attr-defined]
                model=MODEL,
                temperature=0.2,
                messages=messages,
            )
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Legacy OpenAI ChatCompletion call failed")
        else:
            text = _first_text_chunk(response)
            if text:
                return text

    return ""


def _coerce_array(candidate: Any) -> List[Dict[str, Any]]:
    """Extract a list of dicts from *candidate* if possible."""

    if isinstance(candidate, list):
        return [item for item in candidate if isinstance(item, dict)]

    if isinstance(candidate, dict):
        for key in PREFERRED_OBJECT_KEYS:
            value = candidate.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

    return []


def _extract_json_array(raw_text: str) -> List[Dict[str, Any]]:
    """Extract and parse the first JSON array found in *raw_text*.

    OpenAI may occasionally wrap the response with extra prose despite the
    prompt. This helper looks for the first JSON array in the response and
    attempts to parse it. If parsing fails, an empty list is returned.
    """

    if not raw_text:
        return []

    raw_text = raw_text.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = None

    if parsed is not None:
        coerced = _coerce_array(parsed)
        if coerced:
            return coerced

    match = JSON_ARRAY_PATTERN.search(raw_text)
    if not match:
        return []

    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []

    return _coerce_array(parsed)


def _parse_price(value: Union[str, int, float, None]) -> float:
    """Convert *value* to a float, tolerating common formatting."""

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return 0.0

        # Remove common currency symbols and descriptors.
        cleaned = re.sub(r"[a-zA-Z$£€¥CADUSDrs\s]", "", cleaned)
        # Replace thousands separators.
        cleaned = cleaned.replace(",", "")

        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    return 0.0


def _coerce_bool(value: Any) -> bool:
    """Coerce truthy strings and numbers into booleans."""

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value != 0

    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"true", "yes", "y", "1", "available", "in stock"}

    return False


def _normalize_result(item: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure every returned item contains the expected keys."""

    title = item.get("title")
    if not isinstance(title, str) or not title.strip():
        title = "Unknown Product"

    source = item.get("source")
    if not isinstance(source, str) or not source.strip():
        source = "OpenAI"

    link = item.get("link")
    if not isinstance(link, str):
        link = ""

    image = item.get("image")
    if not isinstance(image, str):
        image = ""

    return {
        "title": title,
        "price": _parse_price(item.get("price")),
        "in_stock": _coerce_bool(item.get("in_stock")),
        "source": source,
        "link": link,
        "image": image,
    }


def search_openai(query: str) -> List[Dict[str, Any]]:
    """Use OpenAI to generate product search results for *query*.

    The prompt aggressively instructs the model to return a JSON array. If the
    model still emits additional text, we attempt to extract the first JSON
    array. Any parsing issues simply result in an empty list so the caller can
    handle the fallback behaviour.
    """

    if not query.strip():
        return []

    prompt = PROMPT_TEMPLATE.format(query=query.strip())
    messages = [
        {
            "role": "system",
            "content": (
                "You are PriceScout, an assistant that surfaces pricing "
                "information for repair parts and devices."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    try:
        raw_text = _invoke_openai(messages)
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("OpenAI invocation raised an exception")
        return []

    if not raw_text:
        return []

    results = _extract_json_array(raw_text)
    return [_normalize_result(item) for item in results]
