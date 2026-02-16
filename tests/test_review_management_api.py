import importlib
import os
import sys


def load_app_with_temp_db(tmp_path):
    db_path = tmp_path / "test_reviews.db"
    os.environ["REVIEW_DB_PATH"] = str(db_path)

    if "app" in sys.modules:
        module = importlib.reload(sys.modules["app"])
    else:
        module = importlib.import_module("app")

    return module.app


def test_storefronts_and_overview(tmp_path):
    app = load_app_with_temp_db(tmp_path)
    client = app.test_client()

    storefronts = client.get("/api/storefronts")
    assert storefronts.status_code == 200
    storefront_list = storefronts.get_json()
    assert len(storefront_list) >= 3

    overview = client.get("/api/overview")
    assert overview.status_code == 200
    data = overview.get_json()
    assert data["total_reviews"] >= 1
    assert "average_rating" in data


def test_rule_and_auto_response_flow(tmp_path):
    app = load_app_with_temp_db(tmp_path)
    client = app.test_client()

    storefront_id = client.get("/api/storefronts").get_json()[0]["id"]

    save_rule = client.post(
        "/api/auto-rules",
        json={
            "storefront_id": storefront_id,
            "min_rating": 4,
            "max_rating": 5,
            "template": "Thanks {{reviewer_name}} for trusting {{storefront_name}}!",
        },
    )
    assert save_rule.status_code == 200

    pending = client.get(f"/api/reviews?storefront_id={storefront_id}&status=pending").get_json()
    assert pending

    review_id = pending[0]["id"]
    respond = client.post(f"/api/reviews/{review_id}/respond", json={})
    assert respond.status_code == 200
    response_payload = respond.get_json()
    assert response_payload["status"] == "responded"
    assert response_payload["response_text"]
