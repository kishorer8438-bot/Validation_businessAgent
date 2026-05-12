import json
import pytest
from fastapi.testclient import TestClient
from src.api import app


client = TestClient(app)


def test_root_and_health():
    r = client.get("/")
    assert r.status_code in (200,)
    h = client.get("/health")
    assert h.status_code == 200


def test_validate_payload_minimal(tmp_path):
    # create sample file
    p = tmp_path / "afile.txt"
    p.write_text("content")

    resp = client.post("/validate-payload", json={"file_path": str(p), "document_id": "TESTDOC"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("document_id") == "TESTDOC"
    assert body.get("validation_status") == "SUCCESS"
    assert body.get("validation_result", {}).get("is_valid") is True
