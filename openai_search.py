import json
import os
import re
from typing import Any, Dict, List

try:
    import openai  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised in CI environment
    class _MissingOpenAI:
        class ChatCompletion:  # pylint: disable=too-few-public-methods
            @staticmethod
            def create(*_args, **_kwargs):
                raise RuntimeError("The 'openai' package is required to run searches.")

    openai = _MissingOpenAI()  # type: ignore

openai.api_key = os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

PROMPT_TEMPLATE = """
Return ONLY a valid JSON array (no markdown, no commentary) describing at least
five relevant products for the search query "{query}". Each product must be an
object containing: title (string), price (number), in_stock (boolean), source
(string), link (string URL), and image (string URL). If exact data is unknown,
provide your best estimate and set in_stock to false. Make sure prices are
numeric values (floats) without currency symbols.
""".strip()

JSON_ARRAY_PATTERN = re.compile(r"\[\s*\{.*\}\s*\]", re.DOTALL)


def _extract_json_array(raw_text: str) -> List[Dict[str, Any]]:
    """Extract and parse the first JSON array found in *raw_text*.

    OpenAI may occasionally wrap the response with extra prose despite the
    prompt. This helper looks for the first JSON array in the response and
    attempts to parse it. If parsing fails, an empty list is returned.
    """

    match = JSON_ARRAY_PATTERN.search(raw_text or "")
    if not match:
        return []

    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []

    if isinstance(parsed, list):
        return parsed
    return []


def _normalize_result(item: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure every returned item contains the expected keys."""

    return {
        "title": item.get("title", "Unknown Product"),
        "price": float(item.get("price", 0) or 0),
        "in_stock": bool(item.get("in_stock", False)),
        "source": item.get("source", "OpenAI"),
        "link": item.get("link", ""),
        "image": item.get("image", ""),
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

    try:
        response = openai.ChatCompletion.create(
            model=MODEL,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are PriceScout, an assistant that surfaces pricing "
                        "information for repair parts and devices."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
    except Exception:
        return []

    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    results = _extract_json_array(content)
    return [_normalize_result(item) for item in results]
