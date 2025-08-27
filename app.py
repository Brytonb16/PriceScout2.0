
import logging
import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from scrapers.fixez import scrape_fixez
from scrapers.mengtor import scrape_mengtor
from scrapers.laptopscreen import scrape_laptopscreen
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

    try:
        res = scrape_mobilesentrix(query)
        app.logger.info("MobileSentrix returned %d items", len(res))
        results += res
    except Exception:
        app.logger.exception("Error scraping MobileSentrix")

    try:
        res = scrape_fixez(query)
        app.logger.info("Fixez returned %d items", len(res))
        results += res
    except Exception:
        app.logger.exception("Error scraping Fixez")

    try:
        res = scrape_mengtor(query)
        app.logger.info("Mengtor returned %d items", len(res))
        results += res
    except Exception:
        app.logger.exception("Error scraping Mengtor")

    try:
        res = scrape_laptopscreen(query)
        app.logger.info("Laptopscreen returned %d items", len(res))
        results += res
    except Exception:
        app.logger.exception("Error scraping Laptopscreen")

    if in_stock_only:
        results = [r for r in results if r["in_stock"]]

    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
