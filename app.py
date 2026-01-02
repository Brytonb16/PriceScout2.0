
import logging
import os
from typing import Any, Dict, Optional

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


@app.route('/api/search')
def search():
    query = request.args.get("q", "")
    in_stock_only = request.args.get("inStock", "false").lower() == "true"

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
        enriched.append(item)

    enriched.sort(key=lambda r: r.get("price_value", float("inf")))
    if enriched and enriched[0].get("price_value") is not None:
        best_price = enriched[0]["price_value"]
        for item in enriched:
            item["best_price"] = item.get("price_value") == best_price

    return jsonify(enriched)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
