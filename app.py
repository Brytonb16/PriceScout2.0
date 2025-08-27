
import logging
import os
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from scrapers.fixez import scrape_fixez
from scrapers.laptopscreen import scrape_laptopscreen
from scrapers.mengtor import scrape_mengtor
from scrapers.mobilesentrix import scrape_mobilesentrix

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
CORS(app)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/search')
def search():
    query = request.args.get("q", "")
    in_stock_only = request.args.get("inStock", "false").lower() == "true"

    results = []

    sources = [
        ("MobileSentrix", scrape_mobilesentrix),
        ("Fixez", scrape_fixez),
        ("Mengtor", scrape_mengtor),
        ("Laptopscreen", scrape_laptopscreen),
    ]

    for name, scraper in sources:
        try:
            res = scraper(query)
            app.logger.info("%s returned %d items", name, len(res))
            results.extend(res)
        except Exception:
            app.logger.exception("Error scraping %s", name)

    if in_stock_only:
        results = [r for r in results if r["in_stock"]]

    return jsonify(results)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
