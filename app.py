
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from scrapers.utils import parse_price
from search import search_products

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
CORS(app)

ORDER_DB_PATH = os.environ.get("ORDER_DB_PATH") or os.path.join(
    app.instance_path,
    "orders.db",
)
DB_AVAILABLE = True


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(ORDER_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    global DB_AVAILABLE
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        with _get_db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    store_name TEXT NOT NULL,
                    requester TEXT NOT NULL,
                    needed_by TEXT,
                    priority TEXT,
                    notes TEXT,
                    status TEXT NOT NULL,
                    total_estimated REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    part_name TEXT NOT NULL,
                    vendor TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    quality_score REAL,
                    link TEXT,
                    FOREIGN KEY(order_id) REFERENCES orders(id)
                )
                """
            )
        DB_AVAILABLE = True
    except Exception:
        app.logger.exception("Failed to initialize order database.")
        DB_AVAILABLE = False


@app.before_request
def ensure_db_ready() -> None:
    if not DB_AVAILABLE:
        _init_db()


def _require_db():
    if not DB_AVAILABLE:
        return jsonify({"error": "Order database unavailable."}), 503
    return None


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


def _as_float(value: Any, default: Optional[float] = 0.0) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@app.route('/api/orders', methods=['POST'])
def create_order():
    db_error = _require_db()
    if db_error:
        return db_error
    payload = request.get_json(silent=True) or {}
    store_name = str(payload.get("store_name", "")).strip()
    requester = str(payload.get("requester", "")).strip()
    needed_by = str(payload.get("needed_by", "")).strip()
    priority = str(payload.get("priority", "standard")).strip()
    notes = str(payload.get("notes", "")).strip()
    items = payload.get("items", [])

    if not store_name or not requester or not isinstance(items, list) or not items:
        return jsonify({"error": "store_name, requester, and items are required."}), 400

    normalized_items = []
    total = 0.0
    for item in items:
        part_name = str(item.get("part_name", "")).strip()
        vendor = str(item.get("vendor", "")).strip()
        try:
            quantity = int(item.get("quantity", 1))
        except (TypeError, ValueError):
            quantity = 1
        unit_price = _as_float(item.get("unit_price"), default=0.0) or 0.0
        quality_score = _as_float(item.get("quality_score"), default=None)
        link = str(item.get("link", "")).strip()

        if not part_name or not vendor or quantity <= 0:
            continue

        total += unit_price * quantity
        normalized_items.append(
            {
                "part_name": part_name,
                "vendor": vendor,
                "quantity": quantity,
                "unit_price": unit_price,
                "quality_score": quality_score,
                "link": link,
            }
        )

    if not normalized_items:
        return jsonify({"error": "No valid items supplied."}), 400

    order_id = f"PO-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    with _get_db() as conn:
        conn.execute(
            """
            INSERT INTO orders (id, created_at, store_name, requester, needed_by, priority, notes, status, total_estimated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                created_at,
                store_name,
                requester,
                needed_by,
                priority,
                notes,
                "submitted",
                total,
            ),
        )
        conn.executemany(
            """
            INSERT INTO order_items (order_id, part_name, vendor, quantity, unit_price, quality_score, link)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    order_id,
                    item["part_name"],
                    item["vendor"],
                    item["quantity"],
                    item["unit_price"],
                    item.get("quality_score"),
                    item.get("link"),
                )
                for item in normalized_items
            ],
        )

    return jsonify(
        {
            "id": order_id,
            "created_at": created_at,
            "status": "submitted",
            "total_estimated": round(total, 2),
        }
    )


@app.route('/api/orders', methods=['GET'])
def list_orders():
    db_error = _require_db()
    if db_error:
        return db_error
    limit = min(int(request.args.get("limit", 25)), 100)
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    return jsonify([dict(row) for row in rows])


@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order(order_id: str):
    db_error = _require_db()
    if db_error:
        return db_error
    with _get_db() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            return jsonify({"error": "Order not found."}), 404
        items = conn.execute(
            "SELECT part_name, vendor, quantity, unit_price, quality_score, link FROM order_items WHERE order_id = ?",
            (order_id,),
        ).fetchall()

    return jsonify({"order": dict(order), "items": [dict(item) for item in items]})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
