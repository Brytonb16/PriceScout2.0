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
