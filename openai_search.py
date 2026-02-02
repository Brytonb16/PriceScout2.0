import json
import logging
import os
from typing import Dict, Iterable, List

import openai
from openai import OpenAI

from scrapers.utils import parse_price

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
REQUEST_TIMEOUT_SECONDS = 15

logger = logging.getLogger(__name__)

REWRITE_TEMPLATE = (
    "Rewrite the shopper query so MobileSentrix, Amazon, Ebay, and Fixez listings are easy to find. "
    "Return JSON with keys 'primary' (concise search string) and 'boosted' "
    "(array of 3-5 vendor-augmented queries that explicitly mention MobileSentrix, "
    "Amazon, Ebay, and Fixez). Keep the text short and focused on product terms."
)

SUMMARY_TEMPLATE = (
    "You rank repair part listings. Given the shopper query and a JSON array of "
    "offers, return the 10 lowest priced items. Always include at least one "
    "entry for MobileSentrix, Amazon, Ebay, and Fixez when available in the input. "
    "Output JSON only with the original objects in price order."
)


def _call_chat(prompt: str, user_payload: str) -> str | None:
    """Best-effort call to the configured chat model."""

    if not OPENAI_API_KEY:
        try:
            response = openai.ChatCompletion.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_payload},
                ],
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if isinstance(response, dict):
                return response["choices"][0]["message"]["content"]
            return response.choices[0].message["content"]
        except Exception:
            logger.warning("OpenAI client not configured; skipping request")
            return None

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_payload},
            ],
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        return response.choices[0].message.content
    except Exception:
        logger.exception("OpenAI request failed")
        return None


def rewrite_query_with_vendors(query: str) -> Dict[str, object]:
    """Return OpenAI-guided query variants that surface priority vendors."""

    payload = json.dumps({"query": query})
    content = _call_chat(REWRITE_TEMPLATE, payload)

    if content:
        try:
            parsed = json.loads(content)
            primary = str(parsed.get("primary") or query).strip()
            boosted = [str(item).strip() for item in parsed.get("boosted", []) if str(item).strip()]
            return {"primary": primary or query, "boosted": boosted}
        except Exception:
            pass

    boosted = [
        f"{query} MobileSentrix",
        f"{query} Amazon",
        f"{query} Ebay",
        f"{query} Fixez",
    ]
    return {"primary": query, "boosted": boosted}


def _normalize_price_value(item: Dict[str, object]) -> Dict[str, object]:
    result = dict(item)
    if "price_value" in result:
        return result

    price = result.get("price")
    try:
        result["price_value"] = float(price)
    except (TypeError, ValueError):
        result["price_value"] = parse_price(str(price or "")) if price is not None else float("inf")
    return result


def _fallback_top_offers(results: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    normalized = [_normalize_price_value(item) for item in results]
    required = ("mobilesentrix", "amazon", "ebay", "fixez")

    def matches_vendor(item, vendor):
        return vendor in str(item.get("source", "")).lower()

    top: List[Dict[str, object]] = []
    seen_ids = set()

    for vendor in required:
        for candidate in normalized:
            key = id(candidate)
            if key in seen_ids:
                continue
            if matches_vendor(candidate, vendor):
                top.append(candidate)
                seen_ids.add(key)
                break

    for candidate in sorted(normalized, key=lambda r: r.get("price_value", float("inf"))):
        key = id(candidate)
        if key in seen_ids:
            continue
        top.append(candidate)
        seen_ids.add(key)
        if len(top) >= 10:
            break

    return top[:10]


def summarize_offers_with_openai(query: str, offers: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Use OpenAI to select the 10 best-priced offers, guaranteeing vendor coverage."""

    if not offers:
        return []

    payload = json.dumps({"query": query, "offers": offers})
    content = _call_chat(SUMMARY_TEMPLATE, payload)

    if content:
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed[:10]
        except Exception:
            pass

    return _fallback_top_offers(offers)


def search_openai(query: str):
    """Backward-compatible entrypoint returning AI-synthesised offers."""

    prompt = (
        "You help technicians find replacement and repair parts. "
        "Return a JSON array of 6-10 offers for the search '{query}'. "
        "Each item must include: title, price (as a number), in_stock (boolean), "
        "source (store name), link (product URL), and image (product photo). "
        "Prioritize MobileSentrix, Amazon, and Ebay listings whenever available, "
        "avoid accessories, and sort items by price from lowest to highest so the "
        "best deals appear first."
    ).format(query=query)

    content = _call_chat("You are a helpful product search engine.", prompt)
    if content:
        try:
            return json.loads(content)
        except Exception:
            pass
    return []
