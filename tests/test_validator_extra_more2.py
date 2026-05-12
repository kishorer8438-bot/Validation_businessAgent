import os
from pathlib import Path
import pytest

from src.validator import DataValidator, StandardizedDataValidator


def test_get_file_type_xml_and_config_and_code(tmp_path):
    p_xml = tmp_path / "a.unknown"
    p_xml.write_bytes(b"<?xml version=\"1.0\"?><root></root>")
    dv_xml = DataValidator(str(p_xml))
    assert dv_xml._get_file_type() == "xml"

    p_cfg = tmp_path / "conf.yaml"
    p_cfg.write_text("k: v")
    dv_cfg = DataValidator(str(p_cfg))
    assert dv_cfg._get_file_type() == "config"

    p_code = tmp_path / "script.py"
    p_code.write_text("print('hi')")
    dv_code = DataValidator(str(p_code))
    assert dv_code._get_file_type() == "code"


def test_check_file_readable_succeeds_on_latin1(tmp_path):
    # Create bytes that are invalid UTF-8 but valid latin-1
    p = tmp_path / "latin.txt"
    content = bytes([0xE9, 0x20, 0x41])  # é in latin-1
    p.write_bytes(content)
    dv = DataValidator(str(p))
    # Ensure file existence is true by monkeypatching _get_file_info
    dv._get_file_info = lambda: {"exists": True, "size": p.stat().st_size}
    assert dv.check_file_readable() is True


def test_validate_success_path_and_result_fields(tmp_path):
    p = tmp_path / "ok.txt"
    p.write_text("hello world")
    dv = DataValidator(str(p))
    res = dv.validate()
    assert res["standardized_data"]["validation"]["status"] == "SUCCESS"
    assert "validator_class" in res["standardized_data"]["metadata"]


def test_standardized_validator_accepts_fractional_and_t_formats():
    payload = {
        "document_id": "F1",
        "standardized_data": {
            "file_details": {"file_path": "p", "file_type": "text", "created_at": "2020-01-01T00:00:00.123456"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "SUCCESS"},
            "summary": {"message": "ok", "errors": None},
            "metadata": {"processed_by": "sys", "version": "1.0", "timestamp": "2020-01-01T00:00:00"}
        }
    }
    sd = StandardizedDataValidator(payload)
    res = sd.validate()
    assert res["validation_passed"] is True
