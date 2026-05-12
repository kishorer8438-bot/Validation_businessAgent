import pytest

from src.validator import DataValidator, StandardizedDataValidator
from src.utils import ValidationError


def test_datavalidator_init_empty_path_raises():
    with pytest.raises(ValidationError):
        DataValidator("")


def test_check_file_exists_handles_get_info_exception(monkeypatch, tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("ok")
    dv = DataValidator(str(p))

    def bad_get(path):
        raise Exception("boom")

    monkeypatch.setattr("src.validator.get_file_info", bad_get)
    # check_file_exists should catch and return False
    assert dv.check_file_exists() is False


def test_standardized_schema_summary_errors_type_and_metadata_type():
    payload = {
        "document_id": "S1",
        "standardized_data": {
            "file_details": {"file_path": "p", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "SUCCESS"},
            "summary": {"message": "ok", "errors": 123},
            "metadata": {"processed_by": 5, "version": 6, "timestamp": "2020-01-01 00:00:00"}
        }
    }
    sd = StandardizedDataValidator(payload)
    res = sd.validate()
    assert res["validation_passed"] is False
    assert any("summary.errors must be None or a string" in e for e in res["schema_errors"]) or any("metadata.processed_by" in e for e in res["schema_errors"]) 
