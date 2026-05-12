import json
import datetime
import pytest

from src.validator import DataValidator
from src.utils import FileOperationError


def test_get_file_type_unknown_extension(tmp_path):
    p = tmp_path / "file.unknownext"
    p.write_text("plain content")
    dv = DataValidator(str(p))
    # Should return 'unknown' for unsupported extension and non-matching header
    assert dv._get_file_type() == "unknown"


def test_determine_status_file_not_found_empty_and_unreadable():
    dv = DataValidator.__new__(DataValidator)
    dv.file_path = "no-such-file"

    # FILE_NOT_FOUND
    status = DataValidator._determine_status(dv, False, False, False)
    assert status["status"] == "FILE_NOT_FOUND"

    # EMPTY_FILE
    status2 = DataValidator._determine_status(dv, True, False, True)
    assert status2["status"] == "EMPTY_FILE"

    # UNREADABLE_FILE
    status3 = DataValidator._determine_status(dv, True, True, False)
    assert status3["status"] == "UNREADABLE_FILE"


def test_validate_exception_fallback(monkeypatch, tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("ok")
    dv = DataValidator(str(p))

    # Cause unexpected exception in _get_file_info to hit validate() fallback
    monkeypatch.setattr(DataValidator, "_get_file_info", lambda self: (_ for _ in ()).throw(Exception("boom")))
    res = dv.validate()
    assert res["standardized_data"]["validation"]["status"] == "VALIDATION_ERROR"


def test_to_json_handles_validate_exception(monkeypatch, tmp_path):
    p = tmp_path / "y.txt"
    p.write_text("ok")
    dv = DataValidator(str(p))

    monkeypatch.setattr(DataValidator, "validate", lambda self: (_ for _ in ()).throw(Exception("err")))
    out = dv.to_json()
    parsed = json.loads(out)
    assert parsed.get("error") == "Failed to serialize validation result"


def test_build_standardized_result_includes_validator_class(monkeypatch, tmp_path):
    p = tmp_path / "z.txt"
    p.write_text("ok")
    dv = DataValidator(str(p))

    # Provide controlled file_info and status to build payload
    file_info = {"created": "2020-01-01", "size": 10, "modified": "2020-01-01"}
    status_meta = {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "SUCCESS", "message": "ok", "errors": None}

    res = DataValidator._build_standardized_result(dv, status_meta, file_info)
    assert "standardized_data" in res
    assert res["standardized_data"]["metadata"]["validator_class"] == dv.__class__.__name__
