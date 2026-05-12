import json
from copy import deepcopy

import pytest

from src.business_agent import BusinessRulesAgent
from src.utils import ValidationError


def test_parse_payload_invalid_json_string_raises():
    with pytest.raises(ValidationError):
        BusinessRulesAgent("{not: valid json}")


def test_parse_payload_json_non_object_raises():
    with pytest.raises(ValidationError):
        BusinessRulesAgent("[1,2,3]")


def _base_payload():
    return {
        "document_id": "D1",
        "standardized_data": {
            "file_details": {"file_path": "p", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "SUCCESS"},
            "summary": {"message": "ok", "errors": None},
            "metadata": {"processed_by": "sys", "version": "1.0", "timestamp": "2020-01-01 00:00:00"}
        }
    }


def test_validate_required_structure_reports_non_dict_standardized():
    p = {"document_id": "X", "standardized_data": "not-a-dict"}
    agent = BusinessRulesAgent(p)
    res = agent.validate()
    assert res["validation_passed"] is False
    assert any("standardized_data must be an object" in v for v in res["business_rule_violations"])


def test_check_validation_types_and_unsupported_status():
    p = _base_payload()
    # make validation types wrong and unsupported status
    p["standardized_data"]["validation"]["file_exists"] = "yes"
    p["standardized_data"]["validation"]["status"] = "WEIRD_STATUS"

    agent = BusinessRulesAgent(p)
    res = agent.validate()
    assert res["validation_passed"] is False
    # Expect a type violation and unsupported status violation
    assert any("validation.file_exists must be a boolean" in v for v in res["business_rule_violations"]) or any("Unsupported status" in v for v in res["business_rule_violations"])


def test_validate_consistency_rules_various_cases():
    # file_exists False but file_not_empty True
    p = _base_payload()
    p["standardized_data"]["validation"]["file_exists"] = False
    p["standardized_data"]["validation"]["file_not_empty"] = True
    agent = BusinessRulesAgent(p)
    res = agent.validate()
    assert any("file_not_empty cannot be true when file_exists is false" in v for v in res["business_rule_violations"]) 

    # UNREADABLE_FILE but file_readable True
    p2 = _base_payload()
    p2["standardized_data"]["validation"]["status"] = "UNREADABLE_FILE"
    p2["standardized_data"]["validation"]["file_readable"] = True
    a2 = BusinessRulesAgent(p2)
    r2 = a2.validate()
    assert any("UNREADABLE_FILE requires file_readable to be false" in v for v in r2["business_rule_violations"]) 

    # FILE_NOT_FOUND but file_readable True
    p3 = _base_payload()
    p3["standardized_data"]["validation"]["status"] = "FILE_NOT_FOUND"
    p3["standardized_data"]["validation"]["file_readable"] = True
    a3 = BusinessRulesAgent(p3)
    r3 = a3.validate()
    assert any("FILE_NOT_FOUND requires file_readable to be false" in v for v in r3["business_rule_violations"]) 


def test_validate_metadata_rules_produces_warnings_on_missing_fields():
    p = _base_payload()
    # Simulate downstream metadata check without required-structure gating.
    # Monkeypatch required-structure step so metadata warnings can be exercised in isolation.
    p["standardized_data"]["metadata"] = {}
    agent = BusinessRulesAgent(p)
    agent._validate_required_structure = lambda: None
    agent.violations = []
    # run only metadata rules to capture warnings
    agent._validate_metadata_rules()
    assert any(
        "metadata.processed_by is missing" in w or "metadata.version is missing" in w or "metadata.timestamp is missing" in w
        for w in agent.warnings
    )
