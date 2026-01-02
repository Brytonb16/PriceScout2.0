import scrapers.fixez as fixez


def test_scrape_fixez_filters_irrelevant_results(monkeypatch):
    html = """
    <ul>
      <li class="product-item">
        <a class="product-item-link" href="/iphone-screen">iPhone 13 Screen</a>
        <span class="price">$99.99</span>
        <img src="//images/iphone.jpg" />
      </li>
      <li class="product-item">
        <a class="product-item-link" href="/random-case">Universal Phone Case</a>
        <span class="price">$9.99</span>
        <img src="//images/case.jpg" />
      </li>
    </ul>
    """

    monkeypatch.setattr(fixez, "render_page", lambda *_args, **_kwargs: html)

    results = fixez.scrape_fixez("iphone screen")

    assert len(results) == 1
    assert results[0]["title"] == "iPhone 13 Screen"
