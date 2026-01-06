from scrapers import amazon


SAMPLE_HTML = """
<div data-component-type="s-search-result">
  <h2><a href="/dp/123"><span>Replacement Screen</span></a></h2>
  <span class="a-price">
    <span class="a-offscreen">$24.99</span>
  </span>
  <img class="s-image" src="https://images.test/screen.jpg" />
</div>
"""


def test_parse_results_extracts_core_fields():
    parsed = amazon._parse_results(SAMPLE_HTML)
    assert parsed[0]["title"] == "Replacement Screen"
    assert parsed[0]["link"].startswith("https://www.amazon.com/dp/123")
    assert parsed[0]["price"] == "$24.99"
    assert parsed[0]["price_value"] == 24.99
    assert parsed[0]["source"] == "Amazon"
    assert parsed[0]["image"] == "https://images.test/screen.jpg"


def test_scrape_amazon_handles_missing_html(monkeypatch, caplog):
    caplog.set_level("INFO")
    monkeypatch.setattr(amazon, "render_page", lambda url, wait_selector=None: None)

    assert list(amazon.scrape_amazon("iphone screen")) == []
    assert any("failed" in message for message in caplog.messages)
