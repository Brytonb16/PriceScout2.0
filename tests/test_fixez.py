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


def test_matches_query_prefers_high_overlap(monkeypatch):
    html = """
    <ul>
      <li class="product-item">
        <a class="product-item-link" href="/switch-case">Nintendo Switch Carry Case</a>
        <span class="price">$19.99</span>
        <img src="//images/case.jpg" />
      </li>
      <li class="product-item">
        <a class="product-item-link" href="/joycons">Nintendo Switch Joy-Con (L/R)</a>
        <span class="price">$79.99</span>
        <img src="//images/joycon.jpg" />
      </li>
    </ul>
    """

    monkeypatch.setattr(fixez, "render_page", lambda *_args, **_kwargs: html)

    results = fixez.scrape_fixez("Nintendo Switch Joy Cons")

    assert len(results) == 1
    assert "Joy-Con" in results[0]["title"]


def test_matches_query_dislikes_loose_power_results(monkeypatch):
    html = """
    <ul>
      <li class="product-item">
        <a class="product-item-link" href="/power-board">Power Board for Xbox Series X</a>
        <span class="price">$24.99</span>
        <img src="//images/board.jpg" />
      </li>
      <li class="product-item">
        <a class="product-item-link" href="/power-cable">Power Cable for Xbox Series X</a>
        <span class="price">$12.99</span>
        <img src="//images/cable.jpg" />
      </li>
      <li class="product-item">
        <a class="product-item-link" href="/power-supply">Xbox Series X Power Supply Replacement</a>
        <span class="price">$69.99</span>
        <img src="//images/supply.jpg" />
      </li>
    </ul>
    """

    monkeypatch.setattr(fixez, "render_page", lambda *_args, **_kwargs: html)

    results = fixez.scrape_fixez("xbox series x power supply")

    assert len(results) == 1
    assert "Power Supply" in results[0]["title"]
