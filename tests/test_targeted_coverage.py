import json
import os
from pathlib import Path

import pytest
from src.validator import DataValidator
from src.api import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_get_file_type_pdf_and_archive(tmp_path):
    pdf = tmp_path / "file.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%EOF\n")
    dv_pdf = DataValidator(str(pdf), "DOCPDF")
    res_pdf = dv_pdf.validate()
    ftype_pdf = res_pdf["standardized_data"]["file_details"]["file_type"]
    assert ftype_pdf == "pdf"

    z = tmp_path / "file.docx"
    z.write_bytes(b"PK\x03\x04")
    dv_z = DataValidator(str(z), "DOCZIP")
    res_z = dv_z.validate()
    ftype_z = res_z["standardized_data"]["file_details"]["file_type"]
    # docx may be detected as word or archive depending on implementation
    assert ftype_z in ("archive", "unknown", "word")


def test_validate_payload_enterprise_file_not_found(tmp_path):
    payload = {
        "document_id": "MISSING",
        "file_details": {"file_path": str(tmp_path / "does_not_exist.txt"), "file_name": "does_not_exist.txt", "file_type": "text", "file_size_kb": 1}
    }
    resp = client.post("/validate-payload", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("validation_status") in ("FILE_NOT_FOUND", "VALIDATION_ERROR")


def test_validate_payload_save_output_writes_file(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world")
    out = tmp_path / "out.json"
    resp = client.post("/validate-payload", json={"file_path": str(p), "document_id": "SAVED", "save_output": True, "output_path": str(out)})
    assert resp.status_code == 200
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("document_id") is not None


def test_validate_file_invalid_path_returns_standardized_result():
    resp = client.post("/validate-file", json={"file_path": "nonexistent/path.txt"})
    assert resp.status_code == 200
    body = resp.json()
    assert "standardized_data" in body
    assert body["standardized_data"]["validation"]["status"] in ("FILE_NOT_FOUND", "VALIDATION_ERROR")
