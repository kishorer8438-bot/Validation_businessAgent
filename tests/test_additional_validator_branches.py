import builtins
import json
from pathlib import Path

import pytest

from src.validator import DataValidator, StandardizedDataValidator
from src.business_agent import BusinessRulesAgent
from src.utils import FileOperationError, ValidationError


def test_get_file_type_signature_detection(tmp_path):
    # PDF signature
    p_pdf = tmp_path / "a.pdf"
    p_pdf.write_bytes(b"%PDF-1.4\n%EOF")
    dv_pdf = DataValidator(str(p_pdf))
    assert dv_pdf._get_file_type() == "pdf"

    # ZIP signature (archive)
    p_zip = tmp_path / "b.bin"
    p_zip.write_bytes(b"PK\x03\x04somecontent")
    dv_zip = DataValidator(str(p_zip))
    assert dv_zip._get_file_type() == "archive"

    # JSON content detection
    p_json = tmp_path / "c.unknown"
    p_json.write_bytes(b"{" + b'"k":1' + b"}")
    dv_json = DataValidator(str(p_json))
    assert dv_json._get_file_type() == "json"


def test_get_file_type_handles_path_exists_exception(monkeypatch, tmp_path):
    p = tmp_path / "x"
    p.write_text("ok")

    # Force Path.exists to raise to hit outer exception
    monkeypatch.setattr(Path, "exists", lambda self: (_ for _ in ()).throw(Exception("boom")))

    dv = DataValidator(str(p))
    assert dv._get_file_type() == "unknown"


def test__get_file_info_handles_fileoperationerror(monkeypatch, tmp_path):
    p = tmp_path / "info.txt"
    p.write_text("x")

    def bad_info(path):
        raise FileOperationError("no access")

    monkeypatch.setattr("src.validator.get_file_info", bad_info)

    dv = DataValidator(str(p))
    info = dv._get_file_info()
    assert info == {"exists": False}


def test_check_file_readable_permission_and_unicode_errors(monkeypatch, tmp_path):
    p = tmp_path / "r.txt"
    p.write_text("hello")

    dv = DataValidator(str(p))

    # Ensure file existence checks pass
    monkeypatch.setattr(DataValidator, "_get_file_info", lambda self: {"exists": True, "size": 5})

    # PermissionError branch
    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError()))
    assert dv.check_file_readable() is False

    # UnicodeDecodeError branch (simulates decoding failures across encodings)
    def raise_unicode(*args, **kwargs):
        raise UnicodeDecodeError("utf-8", b"", 0, 1, "fail")

    monkeypatch.setattr(builtins, "open", raise_unicode)
    assert dv.check_file_readable() is False


def test_save_result_success_and_failure(monkeypatch, tmp_path):
    p = tmp_path / "s.txt"
    p.write_text("ok")
    dv = DataValidator(str(p))

    called = {}

    def fake_write_json(path, data, **kwargs):
        called['path'] = str(path)
        called['data'] = data

    # success
    monkeypatch.setattr("src.utils.write_json", fake_write_json)
    dv.save_result(tmp_path / "out.json")
    assert 'path' in called and called['path']

    # failure
    def bad_write(*args, **kwargs):
        raise Exception("disk error")

    monkeypatch.setattr("src.utils.write_json", bad_write)
    with pytest.raises(Exception):
        dv.save_result(tmp_path / "out.json")


def test_standardized_validator_evaluates_business_warnings_and_violations(monkeypatch):
    # Prepare a valid structured payload so schema validation passes
    payload = {
        "document_id": "Z1",
        "standardized_data": {
            "file_details": {"file_path": "p", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "SUCCESS"},
            "summary": {"message": "ok", "errors": None},
            "metadata": {"processed_by": "sys", "version": "1.0", "timestamp": "2020-01-01 00:00:00"}
        }
    }

    # Force business agent to return warnings and violations
    monkeypatch.setattr("src.business_agent.BusinessRulesAgent.validate", lambda self: {"business_rule_violations": ["v1"], "business_warnings": ["w1"]})

    sd = StandardizedDataValidator(payload)
    res = sd.validate()
    assert res["business_rule_violations"] == ["v1"]
    assert res["business_warnings"] == ["w1"]


def test_standardized_to_json_handles_exception(monkeypatch):
    sd = StandardizedDataValidator({"document_id": "A", "standardized_data": {}})
    monkeypatch.setattr(StandardizedDataValidator, "validate", lambda self: (_ for _ in ()).throw(Exception("boom")))
    out = sd.to_json()
    parsed = json.loads(out)
    assert parsed.get("error") == "Failed to serialize payload validation result"


def test_extract_validation_and_summary_raise(monkeypatch):
    payload = {"document_id": "Q", "standardized_data": {}}
    agent = BusinessRulesAgent(payload)
    with pytest.raises(ValidationError):
        agent._extract_validation()
    with pytest.raises(ValidationError):
        agent._extract_summary()
