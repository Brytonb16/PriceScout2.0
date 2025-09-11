
import logging
import os
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from openai_search import search_openai

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

    try:
        results = search_openai(query)
        app.logger.info("OpenAI returned %d items", len(results))
    except Exception:
        app.logger.exception("Error querying OpenAI")
        results = []

    if in_stock_only:
        results = [r for r in results if r.get("in_stock")]

    return jsonify(results)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
