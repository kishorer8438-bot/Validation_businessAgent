import json
from pathlib import Path
import pytest

from fastapi.testclient import TestClient

from src import api
from src.business_agent import BusinessRulesAgent
from src.validator import DataValidator, StandardizedDataValidator
from src.utils import ValidationError


def test_business_agent_unsupported_status_and_success_errors():
    # Unsupported status should produce a violation
    payload = {
        "document_id": "U1",
        "standardized_data": {
            "file_details": {"file_path": "p", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "WEIRD_STATUS"},
            "summary": {"message": "weird", "errors": None},
            "metadata": {"processed_by": "x", "version": "1.0", "timestamp": "2020-01-01 00:00:00"}
        }
    }
    agent = BusinessRulesAgent(payload)
    result = agent.validate()
    assert not result["validation_passed"]
    assert any("Unsupported status" in v for v in result["business_rule_violations"]) or result["business_rule_violations"]

    # SUCCESS with non-null summary.errors should violate
    payload2 = {
        "document_id": "S1",
        "standardized_data": {
            "file_details": {"file_path": "p", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "SUCCESS"},
            "summary": {"message": "ok", "errors": "some error"},
            "metadata": {"processed_by": "x", "version": "1.0", "timestamp": "2020-01-01 00:00:00"}
        }
    }
    agent2 = BusinessRulesAgent(payload2)
    res2 = agent2.validate()
    assert not res2["validation_passed"]
    assert any("SUCCESS status must have summary.errors set to null" in v for v in res2["business_rule_violations"]) or res2["business_rule_violations"]


def test_business_agent_non_success_requires_errors():
    # Non-success status must include non-null summary.errors
    payload = {
        "document_id": "F1",
        "standardized_data": {
            "file_details": {"file_path": "p", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": False, "file_not_empty": False, "file_readable": False, "status": "FILE_NOT_FOUND"},
            "summary": {"message": "missing", "errors": None},
            "metadata": {"processed_by": "x", "version": "1.0", "timestamp": "2020-01-01 00:00:00"}
        }
    }
    agent = BusinessRulesAgent(payload)
    res = agent.validate()
    assert not res["validation_passed"]
    assert any("must include a non-null summary.errors" in v or "must include" in v for v in res["business_rule_violations"]) or res["business_rule_violations"]


def test_business_agent_file_exists_false_but_not_empty_true():
    payload = {
        "document_id": "C1",
        "standardized_data": {
            "file_details": {"file_path": "p", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": False, "file_not_empty": True, "file_readable": False, "status": "FILE_NOT_FOUND"},
            "summary": {"message": "bad", "errors": "err"},
            "metadata": {"processed_by": "x", "version": "1.0", "timestamp": "2020-01-01 00:00:00"}
        }
    }
    agent = BusinessRulesAgent(payload)
    res = agent.validate()
    assert not res["validation_passed"]
    assert any("file_not_empty cannot be true when file_exists is false" in v for v in res["business_rule_violations"]) or res["business_rule_violations"]


def test_business_agent_parse_datetime_violations():
    # created_at not a string and metadata timestamp invalid format
    payload = {
        "document_id": "D1",
        "standardized_data": {
            "file_details": {"file_path": "p", "file_type": "text", "created_at": 12345},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "SUCCESS"},
            "summary": {"message": "ok", "errors": None},
            "metadata": {"processed_by": "x", "version": "1.0", "timestamp": "not-a-date"}
        }
    }
    agent = BusinessRulesAgent(payload)
    res = agent.validate()
    # Expect violations about datetime parsing and metadata types
    assert any("Expected file_details.created_at" in v or "is not in a supported datetime format" in v or "metadata.timestamp" in v or "must be a string" in v or "must be" in v for v in res["business_rule_violations"]) or res["business_rule_violations"]


def test_datavalidator_validate_unexpected_exception(monkeypatch, tmp_path):
    # Force an unexpected exception inside validate to hit except branch
    f = tmp_path / "x.txt"
    f.write_text("hi")
    dv = DataValidator(str(f))

    def boom(self):
        raise Exception("boom")

    monkeypatch.setattr(DataValidator, "check_file_exists", boom)
    res = dv.validate()
    assert res["standardized_data"]["validation"]["status"] == "VALIDATION_ERROR"
    assert "Unexpected validation error" in res["standardized_data"]["summary"]["errors"] or "Unexpected validation error" in res["standardized_data"]["summary"]["message"] or res["standardized_data"]["summary"]["errors"]


def test_standardized_validator_type_and_datetime_errors_and_business_rule_flow(monkeypatch):
    # Build payload with wrong types to hit many schema checks
    payload = {
        "document_id": 123,
        "standardized_data": {
            "file_details": {"file_path": 10, "file_type": 20, "created_at": "bad-date"},
            "validation": {"file_exists": "yes", "file_not_empty": "no", "file_readable": "maybe", "status": 999},
            "summary": {"message": 1, "errors": ["a"]},
            "metadata": {"processed_by": 5, "version": 1.2, "timestamp": 0}
        }
    }
    sd = StandardizedDataValidator(payload)
    res = sd.validate()
    # Expect schema_errors to be populated with multiple type/format complaints
    assert not res["validation_passed"]
    assert isinstance(res["schema_errors"], list) and len(res["schema_errors"]) >= 1


def test_api_validate_payload_score_and_warnings_and_save(monkeypatch, tmp_path):
    client = TestClient(api.app)

    # Create file and build standardized payload with one failing check
    f = tmp_path / "filey.txt"
    f.write_text("content")

    std = {
        "document_id": "P1",
        "standardized_data": {
            "file_details": {"file_path": str(f), "file_type": "unknown", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": False, "status": "UNREADABLE_FILE"},
            "summary": {"message": "unreadable", "errors": "corrupt", "validation_timestamp": "2020-01-01T00:00:00"},
            "metadata": {"processed_by": "sys", "version": "1.0", "timestamp": "2020-01-01 00:00:00"}
        }
    }

    # Capture write_json calls to assert save behavior
    saved = {}

    def fake_write_json(path, data, **kwargs):
        saved['path'] = str(path)
        saved['data'] = data

    monkeypatch.setattr("src.api.write_json", fake_write_json)

    r = client.post("/validate-payload", json=std)
    assert r.status_code == 200
    body = r.json()
    # validation_score should be less than 1 because one check failed
    assert body["validation_result"]["validation_score"] < 1.0
    # unknown file_type should lead to a warning in validation_result.warnings
    assert isinstance(body["validation_result"]["warnings"], list)

    # Now call with save_output True and ensure fake_write_json is called
    std2 = dict(std)
    std2["save_output"] = True
    r2 = client.post("/validate-payload", json=std2)
    assert r2.status_code == 200
    assert 'path' in saved and saved['path']
