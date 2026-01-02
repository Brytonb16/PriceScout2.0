from scrapers import websearch


SAMPLE_HTML = """
<div class="results">
  <div class="result">
    <a class="result__a" href="https://example.com/part-a">Part A</a>
    <div class="result__snippet">Great replacement option.</div>
  </div>
  <div class="result">
    <a class="result__a" href="https://store.test/items/42">Part B</a>
  </div>
</div>
"""


def test_parse_results_extracts_basic_fields():
    parsed = websearch._parse_results(SAMPLE_HTML, "iphone battery")
    assert parsed[0]["title"] == "Part A"
    assert parsed[0]["link"] == "https://example.com/part-a"
    assert parsed[0]["source"] == "example.com"
    assert parsed[0]["snippet"] == "Great replacement option."
    assert parsed[0]["stock_label"] == "Visit site"

    assert parsed[1]["title"] == "Part B"
    assert parsed[1]["source"] == "store.test"


def test_parse_results_decodes_redirects():
    html = """
    <div class="results">
      <div class="result">
        <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fshop.example.com%2Fitem">Redirected</a>
      </div>
    </div>
    """

    parsed = websearch._parse_results(html, "screen replacement")
    assert parsed[0]["link"] == "https://shop.example.com/item"
    assert parsed[0]["source"] == "shop.example.com"


def test_preview_image_for_reads_open_graph(monkeypatch):
    html = """
    <html><head><meta property="og:image" content="https://cdn.test/pic.jpg" /></head></html>
    """

    monkeypatch.setattr(websearch, "safe_get", lambda url: html)

    assert websearch._preview_image_for("https://cdn.test/page") == "https://cdn.test/pic.jpg"


def test_scrape_websearch_uses_safe_get(monkeypatch):
    calls = []

    def fake_safe_get(url, params=None):
        calls.append((url, params))
        return SAMPLE_HTML

    monkeypatch.setattr(websearch, "safe_get", fake_safe_get)

    results = list(websearch.scrape_websearch("iphone battery"))
    assert len(results) == 2
    assert calls[0][0] == websearch.SEARCH_URL
    assert "q" in calls[0][1]


def test_priority_domains_always_get_previews(monkeypatch):
    html = """
    <div class="results">
      <div class="result">
        <a class="result__a" href="https://amazon.com/item1">Item 1</a>
      </div>
      <div class="result">
        <a class="result__a" href="https://ebay.com/item2">Item 2</a>
      </div>
      <div class="result">
        <a class="result__a" href="https://example.com/item3">Item 3</a>
      </div>
    </div>
    """

    previews = {
        "https://amazon.com/item1": {"price": "$10.00", "price_value": 10.0},
        "https://ebay.com/item2": {"price": "$20.00", "price_value": 20.0},
    }

    monkeypatch.setattr(websearch, "safe_get", lambda url, params=None: html if params else "")
    monkeypatch.setattr(websearch, "_preview_details_for", lambda url: previews.get(url, {}))

    results = list(websearch.scrape_websearch("iphone battery"))

    assert results[0]["price"] == "$10.00"
    assert results[1]["price"] == "$20.00"


def test_extract_price_handles_amazon_markup():
    html = """
    <html>
      <span class="a-price">
        <span class="a-price-whole">15</span>
        <span class="a-price-fraction">99</span>
      </span>
    </html>
    """

    soup = websearch.BeautifulSoup(html, "html.parser")
    price = websearch._extract_price_text(soup, "www.amazon.com")

    assert price is not None
    assert "15" in price
