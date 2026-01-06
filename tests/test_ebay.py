from scrapers import ebay


SAMPLE_HTML = """
<ul>
  <li class="s-item">
    <a class="s-item__link" href="https://www.ebay.com/itm/987">Item</a>
    <h3 class="s-item__title">OEM Battery</h3>
    <span class="s-item__price">$12.50</span>
    <img class="s-item__image-img" src="https://img.test/battery.jpg" />
  </li>
</ul>
"""


def test_parse_results_extracts_core_fields():
    parsed = ebay._parse_results(SAMPLE_HTML)
    assert parsed[0]["title"] == "OEM Battery"
    assert parsed[0]["link"] == "https://www.ebay.com/itm/987"
    assert parsed[0]["price"] == "$12.50"
    assert parsed[0]["price_value"] == 12.5
    assert parsed[0]["source"] == "Ebay"
    assert parsed[0]["image"] == "https://img.test/battery.jpg"


def test_scrape_ebay_handles_missing_html(monkeypatch, caplog):
    caplog.set_level("INFO")
    monkeypatch.setattr(ebay, "render_page", lambda url, wait_selector=None: None)

    assert list(ebay.scrape_ebay("iphone battery")) == []
    assert any("failed" in message for message in caplog.messages)
