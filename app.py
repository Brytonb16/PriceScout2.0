import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from search import search_products

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
CORS(app)

DEFAULT_DB_PATH = os.path.join("/tmp", "google_reviews.db")
REVIEW_DB_PATH = os.environ.get("REVIEW_DB_PATH", DEFAULT_DB_PATH)


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(REVIEW_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _init_db() -> None:
    with _get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS storefronts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                city TEXT,
                google_location_id TEXT UNIQUE,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                storefront_id INTEGER NOT NULL,
                reviewer_name TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT NOT NULL,
                review_source TEXT NOT NULL DEFAULT 'google',
                review_date TEXT NOT NULL,
                response_text TEXT,
                responded_at TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                FOREIGN KEY(storefront_id) REFERENCES storefronts(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auto_response_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                storefront_id INTEGER NOT NULL,
                min_rating INTEGER NOT NULL,
                max_rating INTEGER NOT NULL,
                template TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(storefront_id) REFERENCES storefronts(id)
            )
            """
        )

        storefront_count = conn.execute("SELECT COUNT(*) AS count FROM storefronts").fetchone()["count"]
        if storefront_count == 0:
            now = _utc_now()
            conn.executemany(
                """
                INSERT INTO storefronts (name, city, google_location_id, active, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                [
                    ("PriceScout Dallas", "Dallas", "gmb-dallas-001", now),
                    ("PriceScout Austin", "Austin", "gmb-austin-001", now),
                    ("PriceScout Houston", "Houston", "gmb-houston-001", now),
                ],
            )

        review_count = conn.execute("SELECT COUNT(*) AS count FROM reviews").fetchone()["count"]
        if review_count == 0:
            storefronts = conn.execute("SELECT id, name FROM storefronts ORDER BY id").fetchall()
            by_name = {row["name"]: row["id"] for row in storefronts}
            conn.executemany(
                """
                INSERT INTO reviews (storefront_id, reviewer_name, rating, comment, review_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (by_name["PriceScout Dallas"], "Alex R.", 5, "Quick turnaround and fair pricing.", "2026-02-03", "pending"),
                    (by_name["PriceScout Dallas"], "Jamie P.", 2, "Repair was delayed and I had to call twice.", "2026-02-08", "pending"),
                    (by_name["PriceScout Austin"], "Morgan T.", 4, "Friendly team and clear updates.", "2026-02-11", "pending"),
                    (by_name["PriceScout Houston"], "Chris D.", 3, "Good service overall, parking is tough.", "2026-02-12", "pending"),
                ],
            )


_init_db()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/search", methods=["GET"])
def api_search_products():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing query parameter 'q'."}), 400

    results = search_products(query)
    return jsonify({"query": query, "results": results, "count": len(results)})


@app.route("/api/storefronts", methods=["GET"])
def list_storefronts():
    with _get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                s.id,
                s.name,
                s.city,
                s.google_location_id,
                s.active,
                COUNT(r.id) AS total_reviews,
                SUM(CASE WHEN r.status = 'pending' THEN 1 ELSE 0 END) AS pending_reviews,
                ROUND(AVG(CAST(r.rating AS REAL)), 2) AS avg_rating
            FROM storefronts s
            LEFT JOIN reviews r ON r.storefront_id = s.id
            GROUP BY s.id
            ORDER BY s.name ASC
            """
        ).fetchall()

    return jsonify([dict(row) for row in rows])


@app.route("/api/reviews", methods=["GET"])
def list_reviews():
    storefront_id = request.args.get("storefront_id", type=int)
    status = request.args.get("status", "all").strip().lower()

    conditions = []
    values: list[Any] = []
    if storefront_id:
        conditions.append("r.storefront_id = ?")
        values.append(storefront_id)
    if status in {"pending", "responded"}:
        conditions.append("r.status = ?")
        values.append(status)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with _get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT
                r.id,
                r.storefront_id,
                s.name AS storefront_name,
                r.reviewer_name,
                r.rating,
                r.comment,
                r.review_source,
                r.review_date,
                r.response_text,
                r.responded_at,
                r.status
            FROM reviews r
            JOIN storefronts s ON s.id = r.storefront_id
            {where_clause}
            ORDER BY r.review_date DESC, r.id DESC
            """,
            values,
        ).fetchall()

    return jsonify([dict(row) for row in rows])


def _find_matching_rule(conn: sqlite3.Connection, storefront_id: int, rating: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM auto_response_rules
        WHERE storefront_id = ?
          AND is_active = 1
          AND ? BETWEEN min_rating AND max_rating
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (storefront_id, rating),
    ).fetchone()


def _render_template(template: str, review: sqlite3.Row, storefront_name: str) -> str:
    return (
        template.replace("{{reviewer_name}}", review["reviewer_name"])
        .replace("{{storefront_name}}", storefront_name)
        .replace("{{rating}}", str(review["rating"]))
        .replace("{{comment}}", review["comment"])
    )


@app.route("/api/reviews/<int:review_id>/respond", methods=["POST"])
def respond_to_review(review_id: int):
    payload = request.get_json(silent=True) or {}
    manual_response = str(payload.get("response_text", "")).strip()

    with _get_db() as conn:
        review = conn.execute(
            """
            SELECT r.*, s.name AS storefront_name
            FROM reviews r
            JOIN storefronts s ON s.id = r.storefront_id
            WHERE r.id = ?
            """,
            (review_id,),
        ).fetchone()
        if not review:
            return jsonify({"error": "Review not found."}), 404

        if manual_response:
            response_text = manual_response
        else:
            rule = _find_matching_rule(conn, review["storefront_id"], review["rating"])
            if rule:
                response_text = _render_template(rule["template"], review, review["storefront_name"])
            else:
                response_text = (
                    f"Thanks {review['reviewer_name']} for sharing feedback with {review['storefront_name']}. "
                    "We appreciate your support and will keep improving your experience."
                )

        responded_at = _utc_now()
        conn.execute(
            """
            UPDATE reviews
            SET response_text = ?, responded_at = ?, status = 'responded'
            WHERE id = ?
            """,
            (response_text, responded_at, review_id),
        )

    return jsonify(
        {
            "id": review_id,
            "status": "responded",
            "responded_at": responded_at,
            "response_text": response_text,
        }
    )


@app.route("/api/auto-rules", methods=["POST"])
def create_or_update_auto_rule():
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    storefront_id = payload.get("storefront_id")
    min_rating = payload.get("min_rating")
    max_rating = payload.get("max_rating")
    template = str(payload.get("template", "")).strip()

    try:
        storefront_id = int(storefront_id)
        min_rating = int(min_rating)
        max_rating = int(max_rating)
    except (TypeError, ValueError):
        return jsonify({"error": "storefront_id, min_rating, and max_rating must be integers."}), 400

    if storefront_id <= 0 or min_rating < 1 or max_rating > 5 or min_rating > max_rating:
        return jsonify({"error": "Invalid rating range or storefront_id."}), 400
    if not template:
        return jsonify({"error": "template is required."}), 400

    now = _utc_now()

    with _get_db() as conn:
        storefront = conn.execute("SELECT id FROM storefronts WHERE id = ?", (storefront_id,)).fetchone()
        if not storefront:
            return jsonify({"error": "Storefront not found."}), 404

        existing = conn.execute(
            """
            SELECT id FROM auto_response_rules
            WHERE storefront_id = ? AND min_rating = ? AND max_rating = ?
            LIMIT 1
            """,
            (storefront_id, min_rating, max_rating),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE auto_response_rules
                SET template = ?, is_active = 1, updated_at = ?
                WHERE id = ?
                """,
                (template, now, existing["id"]),
            )
            rule_id = existing["id"]
        else:
            cursor = conn.execute(
                """
                INSERT INTO auto_response_rules
                (storefront_id, min_rating, max_rating, template, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (storefront_id, min_rating, max_rating, template, now, now),
            )
            rule_id = cursor.lastrowid

    return jsonify(
        {
            "id": rule_id,
            "storefront_id": storefront_id,
            "min_rating": min_rating,
            "max_rating": max_rating,
            "template": template,
            "updated_at": now,
        }
    )


@app.route("/api/auto-rules", methods=["GET"])
def list_auto_rules():
    storefront_id = request.args.get("storefront_id", type=int)

    query = """
        SELECT ar.id, ar.storefront_id, s.name AS storefront_name, ar.min_rating, ar.max_rating,
               ar.template, ar.is_active, ar.updated_at
        FROM auto_response_rules ar
        JOIN storefronts s ON s.id = ar.storefront_id
    """
    values: list[Any] = []
    if storefront_id:
        query += " WHERE ar.storefront_id = ?"
        values.append(storefront_id)
    query += " ORDER BY ar.updated_at DESC"

    with _get_db() as conn:
        rows = conn.execute(query, values).fetchall()

    return jsonify([dict(row) for row in rows])


@app.route("/api/overview", methods=["GET"])
def get_overview():
    with _get_db() as conn:
        stats = conn.execute(
            """
            SELECT
                COUNT(*) AS total_reviews,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_reviews,
                SUM(CASE WHEN status = 'responded' THEN 1 ELSE 0 END) AS responded_reviews,
                ROUND(AVG(CAST(rating AS REAL)), 2) AS average_rating
            FROM reviews
            """
        ).fetchone()

    return jsonify(dict(stats))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
