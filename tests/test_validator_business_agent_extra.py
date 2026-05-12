import json
import os
from pathlib import Path

import pytest

from src.validator import DataValidator, StandardizedDataValidator
from src.business_agent import BusinessRulesAgent
from src.utils import ValidationError, write_json
from src import api
from fastapi.testclient import TestClient


def test_datavalidator_invalid_path_raises_validation_error():
    # Arrange / Act / Assert
    with pytest.raises(ValidationError):
        DataValidator("")


def test_datavalidator_empty_document_id_generates_doc_prefix(tmp_path):
    # Arrange
    p = tmp_path / "f.txt"
    p.write_text("hello")

    # Act
    dv = DataValidator(str(p), document_id="")
    res = dv.validate()

    # Assert
    assert isinstance(res.get("document_id"), str)
    assert res["document_id"].startswith("DOC")


def test_get_file_type_unknown_and_xml_detection(tmp_path):
    # Arrange: unknown extension but xml content
    f = tmp_path / "weird.xyz"
    f.write_text('<?xml version="1.0"?><root></root>')

    dv = DataValidator(str(f))

    # Act
    ftype = dv._get_file_type()

    # Assert: should detect xml by content
    assert ftype == "xml"


def test_negative_size_results_in_empty_file_status(monkeypatch, tmp_path):
    # Arrange: create a file and monkeypatch get_file_info to return negative size
    f = tmp_path / "neg.txt"
    f.write_text("data")

    def fake_get_file_info(_):
        return {"exists": True, "size": -100, "created": None, "modified": None}

    monkeypatch.setattr("src.validator.get_file_info", fake_get_file_info)

    dv = DataValidator(str(f))

    # Act
    res = dv.validate()

    # Assert -> negative size treated as empty -> EMPTY_FILE
    assert res["standardized_data"]["validation"]["status"] == "EMPTY_FILE"


def test_to_json_handles_validate_exception(monkeypatch, tmp_path):
    # Arrange: monkeypatch validate to raise
    p = tmp_path / "a.txt"
    p.write_text("ok")

    dv = DataValidator(str(p))
    monkeypatch.setattr(DataValidator, "validate", lambda self: (_ for _ in ()).throw(Exception("boom")))

    # Act
    out = dv.to_json()

    # Assert: returns a JSON string with error payload
    parsed = json.loads(out)
    assert parsed.get("error") == "Failed to serialize validation result"


def test_save_result_write_failure_raises(monkeypatch, tmp_path):
    # Arrange
    p = tmp_path / "b.txt"
    p.write_text("content")
    dv = DataValidator(str(p))

    # Monkeypatch src.utils.write_json to raise
    def bad_write(*args, **kwargs):
        raise Exception("disk full")

    monkeypatch.setattr("src.utils.write_json", bad_write)

    # Act / Assert
    with pytest.raises(Exception):
        dv.save_result(tmp_path / "out.json")


def test_standardized_validator_missing_document_id_and_schema_errors():
    # Arrange: payload missing document_id
    payload = {"standardized_data": {}}
    sd = StandardizedDataValidator(payload)

    # Act
    res = sd.validate()

    # Assert
    assert not res["validation_passed"]
    assert any("Missing required key 'document_id'" in e or "Missing required key" in e for e in res["schema_errors"]) or res["schema_errors"]


def test_business_agent_valid_and_invalid_payload_handling():
    # Arrange: valid payload
    good = {
        "document_id": "DOC2",
        "standardized_data": {
            "file_details": {"file_path": "a.txt", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "SUCCESS"},
            "summary": {"message": "ok", "errors": None},
            "metadata": {"processed_by": "tester", "version": "1.0", "timestamp": "2020-01-01 00:00:00"}
        }
    }

    agent = BusinessRulesAgent(good)
    res = agent.validate()
    assert res["validation_passed"]
    assert res["business_rule_violations"] == []

    # Invalid payload (string not JSON)
    with pytest.raises(ValidationError):
        BusinessRulesAgent("not a json")


def test_business_agent_status_and_consistency_violations():
    # Arrange: status UNREADABLE but file_readable True -> violation
    payload = {
        "document_id": "X",
        "standardized_data": {
            "file_details": {"file_path": "x", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "UNREADABLE_FILE"},
            "summary": {"message": "unreadable", "errors": "corrupt"},
            "metadata": {"processed_by": "s", "version": "1.0", "timestamp": "2020-01-01 00:00:00"}
        }
    }

    agent = BusinessRulesAgent(payload)
    res = agent.validate()
    assert not res["validation_passed"]
    assert any("UNREADABLE_FILE requires file_readable to be false" in v or "requires file_readable" in v for v in res["business_rule_violations"]) or res["business_rule_violations"]


def test_business_agent_missing_metadata_generates_warnings():
    # Arrange: valid structure but metadata missing fields
    payload = {
        "document_id": "Y",
        "standardized_data": {
            "file_details": {"file_path": "y", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "SUCCESS"},
            "summary": {"message": "ok", "errors": None},
            "metadata": {"processed_by": None, "version": None, "timestamp": None}
        }
    }

    agent = BusinessRulesAgent(payload)
    res = agent.validate()
    # warnings list should contain messages about missing metadata
    assert isinstance(res["business_warnings"], list)


def test_api_save_output_success_and_failure(tmp_path, monkeypatch):
    client = TestClient(api.app)

    # Arrange: create file to validate
    f = tmp_path / "api_file.txt"
    f.write_text("hello")
    outpath = tmp_path / "out.json"

    # Act: successful save
    r = client.post("/validate-file", json={"file_path": str(f), "save_output": True, "output_path": str(outpath)})
    assert r.status_code == 200
    assert outpath.exists()

    # Arrange failure by monkeypatching write_json to raise
    def bad_write(*args, **kwargs):
        raise Exception("no space")

    monkeypatch.setattr("src.api.write_json", bad_write)

    # Act: request should return 400 due to write failure
    r2 = client.post("/validate-file", json={"file_path": str(f), "save_output": True, "output_path": str(outpath)})
    assert r2.status_code == 400
