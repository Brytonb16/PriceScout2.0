from scrapers import mobilesentrix


SAMPLE_HTML = """
<ul>
  <li class="product-item">
    <a class="product-item-link" href="/iphone-13-pro-lcd">iPhone 13 Pro LCD</a>
    <span class="price">$99.99</span>
    <img src="/images/lcd.jpg" />
  </li>
</ul>
"""


def test_mobilesentrix_falls_back_to_static_fetch(monkeypatch):
    calls = {"render": 0, "safe": 0}

    def fake_render(url, wait_selector=None):
        calls["render"] += 1
        return "<html></html>"  # No items found in rendered version

    def fake_safe_get(url, params=None):
        calls["safe"] += 1
        return SAMPLE_HTML

    monkeypatch.setattr(mobilesentrix, "render_page", fake_render)
    monkeypatch.setattr(mobilesentrix, "safe_get", fake_safe_get)

    results = list(mobilesentrix.scrape_mobilesentrix("iphone 13 pro lcd"))

    assert calls["render"] == 1
    assert calls["safe"] == 1
    assert len(results) == 1
    item = results[0]
    assert item["title"] == "iPhone 13 Pro LCD"
    assert item["price"] == 99.99
    assert item["link"].startswith(mobilesentrix.BASE)
