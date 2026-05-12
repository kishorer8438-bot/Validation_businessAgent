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
        "document_id": "DOC001",
        "document_type": "invoice",
        "source_system": "ERP_System",
        "uploaded_by": "Kishore",
        "uploaded_at": "2026-05-12T10:30:00",
        "file_details": {
            "file_name": "sample.txt",
            "file_path": "rag_project/data/raw/sample.txt",
            "file_type": "text",
            "file_size_kb": 1
        },
        "customer_details": {
            "customer_id": "CUST1001",
            "customer_name": "ABC Technologies",
            "customer_email": "abc@example.com"
        }
    }

    response = client.post("/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "status" in data.get("standardized_data", {}).get("validation", {})   # check nested status


# ❌ Test 3: Invalid payload (empty data)
def test_invalid_payload():
    # Missing required fields (no file_details)
    payload = {
        "document_id": "",
        "document_type": "",
        "source_system": "",
        "uploaded_by": "",
        "uploaded_at": "",
        "customer_details": {}
    }

    response = client.post("/validate", json=payload)
    assert response.status_code == 422 or response.status_code == 400


# ❌ Test 4: Missing field
def test_missing_field():
    # Missing file_details entirely
    payload = {
        "document_id": "DOC002",
        "document_type": "invoice",
        "source_system": "ERP_System",
        "uploaded_by": "Kishore",
        "uploaded_at": "2026-05-12T10:30:00"
    }

    response = client.post("/validate", json=payload)
    assert response.status_code == 422 or response.status_code == 400


# ❌ Test 5: Wrong data type
def test_wrong_datatype():
    # Wrong data types in enterprise schema (file_size_kb should be int)
    payload = {
        "document_id": "DOC003",
        "document_type": "invoice",
        "source_system": "ERP_System",
        "uploaded_by": "Kishore",
        "uploaded_at": "2026-05-12T10:30:00",
        "file_details": {
            "file_name": "invoice_003.pdf",
            "file_path": "data/raw/invoice_003.pdf",
            "file_type": "pdf",
            "file_size_kb": "two hundred"
        },
        "customer_details": {
            "customer_id": "CUST1003",
            "customer_name": "XYZ Corp",
            "customer_email": "xyz@example.com"
        }
    }

    response = client.post("/validate", json=payload)
    assert response.status_code == 422 or response.status_code == 400