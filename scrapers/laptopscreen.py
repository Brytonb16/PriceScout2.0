
def scrape_laptopscreen(query):
    return [{
        "title": "Laptopscreen Result for '{}'".format(query),
        "price": 19.99,
        "in_stock": True,
        "source": "Laptopscreen",
        "link": "https://laptopscreen.com/search?q=" + query,
        "image": "https://via.placeholder.com/100"
    }]
