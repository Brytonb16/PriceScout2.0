
def scrape_fixez(query):
    return [{
        "title": "Fixez Result for '{}'".format(query),
        "price": 19.99,
        "in_stock": True,
        "source": "Fixez",
        "link": "https://fixez.com/search?q=" + query,
        "image": "https://via.placeholder.com/100"
    }]
