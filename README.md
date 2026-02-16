# Google Review Command Center

A Flask-based starter build to replace BirdEye for Google review management across multiple storefronts.

## What this build does

- Centralizes Google reviews from multiple storefronts in one dashboard.
- Tracks pending vs responded reviews.
- Supports rule-based auto responses by rating range per storefront.
- Allows one-click responding to reviews using either a matching template or default fallback copy.

## Quick start

1. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
2. Run the server
   ```bash
   python app.py
   ```
3. Open the app
   ```
   http://localhost:5000
   ```

## API overview

- `GET /api/storefronts` — list storefronts with review metrics.
- `GET /api/reviews?storefront_id=<id>&status=pending|responded` — list reviews with filters.
- `POST /api/reviews/<review_id>/respond` — mark review as responded (manual text optional).
- `GET /api/overview` — high-level review counts.
- `POST /api/auto-rules` — create/update auto-response templates.
- `GET /api/auto-rules` — list configured templates.

## Notes for production

- Connect to Google Business Profile APIs/webhooks for live review ingestion.
- Add background jobs for scheduled/approved auto-publishing.
- Add role-based access control and audit logs before production use.
