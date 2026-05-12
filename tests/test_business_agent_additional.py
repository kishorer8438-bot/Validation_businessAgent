import json
import pytest
from src.business_agent import BusinessRulesAgent
from src.utils import ValidationError


def make_base_standardized():
    return {
        "document_id": "DOCX",
        "standardized_data": {
            "file_details": {"file_path": "data/raw/sample.txt", "file_type": "text", "created_at": "2026-05-12T10:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "SUCCESS"},
            "summary": {"message": "OK", "errors": None},
            "metadata": {"processed_by": "RAG", "version": "1.0", "timestamp": "2026-05-12T10:00:00"}
        }
    }


def test_parse_payload_invalid_string_raises():
    with pytest.raises(ValidationError):
        BusinessRulesAgent('{invalid-json}')


def test_missing_required_keys_reports_violation():
    payload = {"document_id": "X"}
    agent = BusinessRulesAgent(payload)
    res = agent.validate()
    assert res["validation_passed"] is False
    assert any("Missing required key" in v for v in res["business_rule_violations"]) is True


def test_status_rules_violation_error_on_success_with_errors():
    p = make_base_standardized()
    # make SUCCESS but provide non-null errors
    p["standardized_data"]["summary"]["errors"] = "some error"
    agent = BusinessRulesAgent(p)
    res = agent.validate()
    assert res["validation_passed"] is False
    assert any("SUCCESS status must have summary.errors set to null" in v for v in res["business_rule_violations"]) 


def test_consistency_rules_file_not_found_and_not_empty():
    p = make_base_standardized()
    p["standardized_data"]["validation"]["file_exists"] = False
    p["standardized_data"]["validation"]["file_not_empty"] = True
    agent = BusinessRulesAgent(p)
    res = agent.validate()
    assert any("file_not_empty cannot be true when file_exists is false" in v for v in res["business_rule_violations"]) 


def test_metadata_warnings_when_missing():
    p = make_base_standardized()
    # remove metadata fields
    p["standardized_data"]["metadata"] = {}
    agent = BusinessRulesAgent(p)
    res = agent.validate()
    assert res["validation_passed"] is False
    # metadata absence may be reported as violations or warnings depending on validation flow
    assert len(res["business_warnings"]) + len(res["business_rule_violations"]) >= 1
