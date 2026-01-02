import scrapers.local_catalog as local_catalog


def test_scrape_local_catalog_matches_keywords():
    results = list(local_catalog.scrape_local_catalog("iphone 12 screen"))
    assert results
    assert any("iphone 12" in item["title"].lower() for item in results)


def test_scrape_local_catalog_sorts_by_score_then_price():
    results = list(local_catalog.scrape_local_catalog("fan replacement"))
    # Expect console fan before GPU fans due to higher keyword overlap and lower price
    titles = [item["title"] for item in results]
    assert titles[0].startswith("Nintendo Switch Internal Cooling Fan")
    assert any(title.startswith("GeForce RTX 3070") for title in titles)
