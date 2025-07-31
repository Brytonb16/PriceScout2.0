
import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from scrapers.mobilesentrix import scrape_mobilesentrix
from scrapers.fixez import scrape_fixez
from scrapers.mengtor import scrape_mengtor
from scrapers.laptopscreen import scrape_laptopscreen

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/search')
def search():
    query = request.args.get("q", "")
    in_stock_only = request.args.get("inStock", "false").lower() == "true"

    results = []
    results += scrape_mobile_sentrix(query)
    results += scrape_fixez(query)
    results += scrape_mengtor(query)
    results += scrape_laptopscreen(query)

    if in_stock_only:
        results = [r for r in results if r["in_stock"]]

    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
