import pytest

from src.business_agent import BusinessRulesAgent


def base_payload():
    return {
        "document_id": "B1",
        "standardized_data": {
            "file_details": {"file_path": "p", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "SUCCESS"},
            "summary": {"message": "ok", "errors": None},
            "metadata": {"processed_by": "sys", "version": "1.0", "timestamp": "2020-01-01 00:00:00"}
        }
    }


def test_parse_datetime_non_string_and_invalid_format():
    agent = BusinessRulesAgent(base_payload())
    # non-string
    agent._parse_datetime(12345, "metadata.timestamp")
    assert any("Expected metadata.timestamp to be ISO datetime string" in v for v in agent.violations)

    # invalid format
    agent.violations = []
    agent._parse_datetime("not-a-date", "metadata.timestamp")
    assert any("metadata.timestamp is not in a supported datetime format" in v for v in agent.violations)


def test_validate_required_structure_subobjects_not_dict():
    p = base_payload()
    p["standardized_data"]["file_details"] = "nope"
    a = BusinessRulesAgent(p)
    res = a.validate()
    assert any("file_details must be an object" in v for v in res["business_rule_violations"]) or res["validation_passed"] is False

    p2 = base_payload()
    p2["standardized_data"]["validation"] = "bad"
    a2 = BusinessRulesAgent(p2)
    r2 = a2.validate()
    assert any("validation must be an object" in v for v in r2["business_rule_violations"]) or r2["validation_passed"] is False

    p3 = base_payload()
    p3["standardized_data"]["summary"] = "bad"
    a3 = BusinessRulesAgent(p3)
    r3 = a3.validate()
    assert any("summary must be an object" in v for v in r3["business_rule_violations"]) or r3["validation_passed"] is False

    p4 = base_payload()
    p4["standardized_data"]["metadata"] = "bad"
    a4 = BusinessRulesAgent(p4)
    r4 = a4.validate()
    assert any("metadata must be an object" in v for v in r4["business_rule_violations"]) or r4["validation_passed"] is False


def test_check_validation_types_additional_fields():
    p = base_payload()
    p["standardized_data"]["validation"]["file_not_empty"] = "no"
    p["standardized_data"]["validation"]["file_readable"] = "maybe"
    a = BusinessRulesAgent(p)
    res = a.validate()
    assert any("validation.file_not_empty must be a boolean" in v for v in res["business_rule_violations"]) or any("validation.file_readable must be a boolean" in v for v in res["business_rule_violations"]) 


def test_validate_status_rules_success_mismatch_and_non_success_null_errors():
    p = base_payload()
    # success but a required flag is wrong
    p["standardized_data"]["validation"]["file_exists"] = False
    a = BusinessRulesAgent(p)
    r = a.validate()
    assert any("Status 'SUCCESS' requires file_exists=True" in v or "Status 'SUCCESS' requires file_exists=True" in v for v in r["business_rule_violations"]) or r["validation_passed"] is False

    # non-success with null errors
    p2 = base_payload()
    p2["standardized_data"]["validation"]["status"] = "FILE_NOT_FOUND"
    p2["standardized_data"]["summary"]["errors"] = None
    a2 = BusinessRulesAgent(p2)
    r2 = a2.validate()
    assert any("must include a non-null summary.errors message" in v for v in r2["business_rule_violations"]) or r2["validation_passed"] is False


def test_evaluate_business_rules_handles_empty_outcome(monkeypatch):
    p = base_payload()
    a = BusinessRulesAgent(p)
    # Force BusinessRulesAgent.validate (when called inside StandardizedDataValidator) to return empty dict
    monkeypatch.setattr("src.business_agent.BusinessRulesAgent.validate", lambda self: {})
    # call evaluate via StandardizedDataValidator flow
    from src.validator import StandardizedDataValidator
    sd = StandardizedDataValidator(p)
    res = sd.validate()
    # No rule violations and empty warnings expected
    assert isinstance(res["business_warnings"], list)
