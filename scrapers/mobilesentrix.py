
def scrape_mobilesentrix(query):
    return [{
        "title": "Mobilesentrix Result for '{}'".format(query),
        "price": 19.99,
        "in_stock": True,
        "source": "Mobilesentrix",
        "link": "https://mobilesentrix.com/search?q=" + query,
        "image": "https://via.placeholder.com/100"
    }]
