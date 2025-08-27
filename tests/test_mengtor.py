from scrapers import mengtor

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

def test_scrape_mengtor(monkeypatch):
    monkeypatch.setattr(mengtor, "render_page", lambda url, wait_selector=None: SEARCH_HTML)
    results = mengtor.scrape_mengtor("screen")
    assert len(results) == 2
    first = results[0]
    assert first["title"] == "Item One"
    assert first["price"] == 10.0
    assert first["link"] == "https://www.mengtor.com/p1"
    assert first["image"] == "https://www.mengtor.com/img1.jpg"
    assert first["source"] == "Mengtor"
