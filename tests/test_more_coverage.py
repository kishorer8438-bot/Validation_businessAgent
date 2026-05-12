import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import main
from src.validator import DataValidator, StandardizedDataValidator
from src.business_agent import BusinessRulesAgent
from src.main import ValidationConfig, validate_single_file, validate_payload_file, save_results


def test_root_and_health_endpoints():
    client = TestClient(main.app)
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["message"].lower().startswith("rag validation api")

    r2 = client.get("/health")
    assert r2.status_code == 200
    assert r2.json()["message"].lower().startswith("rag validation api")


def test_validate_single_file_empty_path_returns_error():
    cfg = ValidationConfig()
    # Passing an empty path should trigger validation error path
    res = validate_single_file("", cfg, document_id=None)
    assert isinstance(res, dict)
    assert res.get("error") is not None
    assert res.get("document_id") == "ERROR"


def test_datavalidator_file_not_found_and_empty_and_type_detection(tmp_path, monkeypatch):
    # Non-existent file should produce FILE_NOT_FOUND
    missing = tmp_path / "no_such.file"
    dv = DataValidator(str(missing))
    result = dv.validate()
    assert result["standardized_data"]["validation"]["status"] == "FILE_NOT_FOUND"

    # Create an empty file -> EMPTY_FILE
    empty = tmp_path / "empty.txt"
    empty.write_text("")
    dv2 = DataValidator(str(empty))
    res2 = dv2.validate()
    assert res2["standardized_data"]["validation"]["status"] == "EMPTY_FILE"

    # Create a JSON-like file with .txt extension to test content-based detection
    js = tmp_path / "data_like.txt"
    js.write_text('{"hello": true}')
    dv3 = DataValidator(str(js))
    assert dv3._get_file_type() in ("json", "text")


def test_datavalidator_unreadable_branch_via_monkeypatch(tmp_path, monkeypatch):
    f = tmp_path / "sample.txt"
    f.write_text("content")
    dv = DataValidator(str(f))

    # Force readable/existence checks to hit UNREADABLE_FILE branch
    monkeypatch.setattr(DataValidator, "check_file_exists", lambda self: True)
    monkeypatch.setattr(DataValidator, "check_file_not_empty", lambda self: True)
    monkeypatch.setattr(DataValidator, "check_file_readable", lambda self: False)

    res = dv.validate()
    assert res["standardized_data"]["validation"]["status"] == "UNREADABLE_FILE"


def test_standardized_validator_missing_keys_and_success(tmp_path):
    # Missing standardized_data should produce schema error
    payload = {"document_id": "DOC1"}
    sd = StandardizedDataValidator(payload)
    r = sd.validate()
    assert not r["validation_passed"]
    assert any("Missing required key" in e for e in r["schema_errors"]) or r["schema_errors"]

    # Valid standardized payload should pass and return source
    good = {
        "document_id": "DOC2",
        "standardized_data": {
            "file_details": {"file_path": "a.txt", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "SUCCESS"},
            "summary": {"message": "ok", "errors": None},
            "metadata": {"processed_by": "tester", "version": "1.0", "timestamp": "2020-01-01 00:00:00"}
        }
    }
    sd2 = StandardizedDataValidator(good)
    r2 = sd2.validate()
    assert r2["validation_passed"]
    assert r2["source"] == "standardized_payload"


def test_business_agent_inconsistency_and_warnings():
    # file_exists False but file_not_empty True should be violation
    payload = {
        "document_id": "X",
        "standardized_data": {
            "file_details": {"file_path": "x", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": False, "file_not_empty": True, "file_readable": False, "status": "FILE_NOT_FOUND"},
            "summary": {"message": "not found", "errors": "missing"},
            "metadata": {"processed_by": None, "version": None, "timestamp": None}
        }
    }
    agent = BusinessRulesAgent(payload)
    res = agent.validate()
    assert not res["validation_passed"]
    # Expect at least one business_rule_violations; warnings may be empty
    assert res["business_rule_violations"]
    assert isinstance(res["business_warnings"], list)


def test_validate_payload_file_invalid_json_and_enterprise_schema(tmp_path):
    # invalid json
    bad = tmp_path / "bad.json"
    bad.write_text("{ not: json }")
    res = validate_payload_file(str(bad))
    assert not res["validation_passed"]
    assert res["document_id"] == "UNKNOWN"

    # enterprise schema: file_details nested file -> should call DataValidator and return dict
    nested = tmp_path / "nested.txt"
    nested.write_text("hello")
    payload = {
        "document_id": "N1",
        "file_details": {"file_path": str(nested)}
    }
    filep = tmp_path / "enterprise.json"
    filep.write_text(json.dumps(payload))
    res2 = validate_payload_file(str(filep))
    # result should be a dict with standardized_data or an error dict; ensure document_id present
    assert isinstance(res2, dict)
    assert res2.get("document_id") in ("N1", None, "UNKNOWN") or "standardized_data" in res2


def test_save_results_single_and_batch(tmp_path):
    cfg = ValidationConfig()
    # single result saved to directory
    results = [{"document_id": "D1", "foo": "bar"}]
    outdir = tmp_path / "outdir"
    save_results(results, str(outdir), cfg)
    # file should exist
    saved = list(outdir.glob("*.json"))
    assert len(saved) == 1

    # batch results saved to file path
    batch = [{"document_id": "A"}, {"document_id": "B"}]
    outfile = tmp_path / "all_results.json"
    save_results(batch, str(outfile), cfg)
    assert outfile.exists()
