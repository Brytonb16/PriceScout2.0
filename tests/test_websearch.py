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
    parsed = websearch._parse_results(SAMPLE_HTML)
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

    parsed = websearch._parse_results(html)
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
