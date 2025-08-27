from scrapers import laptopscreen

SEARCH_HTML = """
<ul>
<li class="product-item">
  <a class="product-item-link" href="/p1">Item One</a>
  <img src="/img1.jpg"/>
  <span class="price">$10.00</span>
</li>
<li class="product-item">
  <a class="product-item-link" href="/p2">Item Two</a>
  <img src="/img2.jpg"/>
  <span class="price">$20.00</span>
</li>
</ul>
"""

def test_scrape_laptopscreen(monkeypatch):
    monkeypatch.setattr(laptopscreen, "render_page", lambda url, wait_selector=None: SEARCH_HTML)
    results = laptopscreen.scrape_laptopscreen("screen")
    assert len(results) == 2
    first = results[0]
    assert first["title"] == "Item One"
    assert first["price"] == 10.0
    assert first["link"] == "https://www.laptopscreen.com/p1"
    assert first["image"] == "https://www.laptopscreen.com/img1.jpg"
    assert first["source"] == "Laptopscreen"
