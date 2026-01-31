from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_chat_basic_search():
    res = client.get("/chat", params={"message": "Show me jackets"})
    assert res.status_code == 200
    body = res.json()
    assert "reply" in body