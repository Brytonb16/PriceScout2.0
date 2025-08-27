import pytest
from scrapers.utils import parse_price

def test_parse_price_single():
    assert parse_price("Starting at $1,234.50") == pytest.approx(1234.50)

def test_parse_price_range():
    assert parse_price("$10–$20") == pytest.approx(15.0)

def test_parse_price_malformed():
    assert parse_price("Free") == 0.0
