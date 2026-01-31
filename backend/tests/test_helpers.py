import pytest
from main import (
    extract_price_constraint,
    detect_size,
    detect_category_keyword,
    detect_gender_department,
)

def test_extract_price_under():
    price, op = extract_price_constraint("Show me jackets under $10")
    assert price == 10
    assert op == "under"

def test_extract_price_over():
    price, op = extract_price_constraint("Show me jackets over $50")
    assert price == 50
    assert op == "over"

def test_extract_price_exact():
    price, op = extract_price_constraint("Show me $25 jackets")
    assert price == 25
    assert op == "exact"

def test_detect_size():
    assert detect_size("small jacket") == "s"
    assert detect_size("Medium hoodie") == "m"
    assert detect_size("XL coat") == "xl"

def test_detect_category():
    assert detect_category_keyword("winter jackets") == "jacket"
    assert detect_category_keyword("nice dress") == "dress"

def test_detect_gender_department():
    assert detect_gender_department("gift for my girlfriend") == "Women"
    assert detect_gender_department("gift for my father") == "Men"