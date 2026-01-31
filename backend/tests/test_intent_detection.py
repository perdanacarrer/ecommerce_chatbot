from main import detect_intent

def test_compare_intent():
    assert detect_intent("What's the difference between these jackets?") == "compare"

def test_gift_intent():
    assert detect_intent("I need a gift for my girlfriend") == "gift"

def test_search_intent():
    assert detect_intent("Show me winter jackets under $50") == "price_search"