import json
import datetime

import pytest

from src.business_agent import BusinessRulesAgent
from src.utils import ValidationError


def minimal_valid_payload():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "document_id": "DOC1",
        "standardized_data": {
            "file_details": {
                "file_path": "data/raw/sample.txt",
                "file_type": "text",
                "created_at": now,
            },
            "validation": {
                "file_exists": True,
                "file_not_empty": True,
                "file_readable": True,
                "status": "SUCCESS",
            },
            "summary": {"message": "ok", "errors": None},
            "metadata": {"processed_by": "x", "version": "1.0", "timestamp": now},
        },
    }


def test_invalid_json_string_raises():
    bad = "{not: valid"
    with pytest.raises(ValidationError):
        BusinessRulesAgent(bad)


def test_non_dict_payload_raises():
    with pytest.raises(ValidationError):
        BusinessRulesAgent([1, 2, 3])


def test_missing_required_keys_reported():
    agent = BusinessRulesAgent({})
    res = agent.validate()
    assert res["validation_passed"] is False
    assert any("Missing required key" in v for v in res["business_rule_violations"]) 


def test_status_success_with_errors_detected():
    p = minimal_valid_payload()
    # make SUCCESS but include errors (should be null)
    p["standardized_data"]["summary"]["errors"] = "some error"
    agent = BusinessRulesAgent(p)
    res = agent.validate()
    assert res["validation_passed"] is False
    assert any("SUCCESS status must have summary.errors set to null" in v for v in res["business_rule_violations"]) 


def test_validation_type_mismatch():
    p = minimal_valid_payload()
    # invalid type for file_exists
    p["standardized_data"]["validation"]["file_exists"] = "yes"

    agent = BusinessRulesAgent(p)
    res = agent.validate()
    assert res["validation_passed"] is False
    assert any("validation.file_exists must be a boolean" in v for v in res["business_rule_violations"]) 


def test_metadata_warnings():
    p = minimal_valid_payload()
    # leave timestamp present but make processed_by/version None to trigger warnings
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    p["standardized_data"]["metadata"] = {"processed_by": None, "version": None, "timestamp": now}

    agent = BusinessRulesAgent(p)
    res = agent.validate()
    # Implementation currently treats missing/None metadata as a violation
    assert res["validation_passed"] is False
    assert any("metadata.processed_by" in v or "metadata.version" in v for v in res["business_rule_violations"]) 
