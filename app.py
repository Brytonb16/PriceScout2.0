
import logging
import os
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, Optional

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from scrapers.utils import parse_price
from search import search_products

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
CORS(app)


@app.route('/')
def home():
    return render_template('index.html')


def _price_value(raw_price: Any) -> Optional[float]:
    """Return a numeric price for sorting or ``None`` when unavailable."""

    if isinstance(raw_price, (int, float)):
        return float(raw_price)
    if isinstance(raw_price, str) and raw_price.strip():
        return parse_price(raw_price)
    return None


def _relevance_score(query: str, title: Any) -> float:
    """Return similarity score between the search *query* and *title*."""

    title_text = str(title or "").strip().lower()
    if not query.strip() or not title_text:
        return 0.0

    return SequenceMatcher(None, query.lower(), title_text).ratio()


def _mark_best_price(items: Iterable[Dict[str, Any]]) -> None:
    """Annotate items with ``best_price`` flag for the lowest priced offer."""

    priced = [i for i in items if i.get("price_value") is not None]
    if not priced:
        return

    best_price = min(i["price_value"] for i in priced)
    for item in items:
        item["best_price"] = item.get("price_value") == best_price


def _sort_results(items: list[Dict[str, Any]], sort: str) -> list[Dict[str, Any]]:
    """Return sorted items based on the requested *sort* mode."""

    if sort == "price":
        return sorted(
            items,
            key=lambda r: (r.get("price_value", float("inf")), -r.get("relevance", 0.0)),
        )

    if sort == "match":
        return sorted(
            items,
            key=lambda r: (-r.get("relevance", 0.0), r.get("price_value", float("inf"))),
        )

    # Default: prioritize closest match, then cheapest.
    return sorted(
        items,
        key=lambda r: (-r.get("relevance", 0.0), r.get("price_value", float("inf"))),
    )


@app.route('/api/search')
def search():
    query = request.args.get("q", "")
    in_stock_only = request.args.get("inStock", "false").lower() == "true"
    sort_mode = request.args.get("sort", "match").lower()

    try:
        results = list(search_products(query))
        app.logger.info("Search returned %d items", len(results))
    except Exception:
        app.logger.exception("Error querying backends")
        results = []

    if in_stock_only:
        results = [r for r in results if r.get("in_stock")]

    enriched: list[Dict[str, Any]] = []
    for result in results:
        item: Dict[str, Any] = dict(result)
        price_val = _price_value(item.get("price"))
        if price_val is not None:
            item["price_value"] = price_val
        item["relevance"] = _relevance_score(query, item.get("title"))
        enriched.append(item)

    _mark_best_price(enriched)
    enriched = _sort_results(enriched, sort_mode)

    return jsonify(enriched)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
