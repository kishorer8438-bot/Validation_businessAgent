from fastapi.testclient import TestClient
from src.api import app   # main.py la app irukkanum

client = TestClient(app)


# ✅ Test 1: Home route (optional but useful)
def test_home():
    response = client.get("/")
    assert response.status_code == 200


# ✅ Test 2: Valid payload
def test_valid_payload():
    payload = {
        "file_path": "rag_project/data/raw/sample.txt",
        "document_id": "DOC001"
    }

    response = client.post("/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "status" in data.get("standardized_data", {}).get("validation", {})   # check nested status


# ❌ Test 3: Invalid payload (empty data)
def test_invalid_payload():
    payload = {
        "document_id": "",
        "standardized_data": {}
    }

    response = client.post("/validate", json=payload)
    assert response.status_code == 422


# ❌ Test 4: Missing field
def test_missing_field():
    payload = {
        "standardized_data": {
            "name": "John"
        }
    }

    response = client.post("/validate", json=payload)
    assert response.status_code == 422


# ❌ Test 5: Wrong data type
def test_wrong_datatype():
    payload = {
        "document_id": "DOC001",
        "standardized_data": {
            "name": "John",
            "invoice_no": "INV-001",
            "amount": "five thousand"   # wrong type
        }
    }

    response = client.post("/validate", json=payload)
    assert response.status_code == 422