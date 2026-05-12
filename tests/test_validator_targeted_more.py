import json
import pytest

from src.validator import DataValidator, StandardizedDataValidator
from src.utils import FileOperationError


def test_get_file_type_word_and_excel(tmp_path):
    p_docx = tmp_path / "doc.docx"
    p_docx.write_bytes(b"PK\x03\x04docx")
    dv1 = DataValidator(str(p_docx))
    assert dv1._get_file_type() == "word"

    p_xlsx = tmp_path / "sheet.xlsx"
    p_xlsx.write_bytes(b"PK\x03\x04xlsx")
    dv2 = DataValidator(str(p_xlsx))
    assert dv2._get_file_type() == "excel"


def test_check_file_readable_handles_os_error(monkeypatch, tmp_path):
    p = tmp_path / "r.txt"
    p.write_text("hi")
    dv = DataValidator(str(p))
    monkeypatch.setattr(DataValidator, "_get_file_info", lambda self: {"exists": True, "size": 2})

    def raise_os(*args, **kwargs):
        raise OSError("disk error")

    monkeypatch.setattr("builtins.open", raise_os)
    assert dv.check_file_readable() is False


def test_get_file_info_handles_fileoperationerror_variation(monkeypatch, tmp_path):
    p = tmp_path / "info2.txt"
    p.write_text("x")
    dv = DataValidator(str(p))

    def bad_info(path):
        raise FileOperationError("cannot stat")

    monkeypatch.setattr("src.validator.get_file_info", bad_info)
    info = dv._get_file_info()
    assert info == {"exists": False}


def test_standardized_schema_type_and_datetime_errors():
    # malformed schema: wrong types and bad datetime
    payload = {
        "document_id": "DOC",
        "standardized_data": {
            "file_details": {"file_path": 123, "file_type": [], "created_at": "bad-date"},
            "validation": {"file_exists": "yes", "file_not_empty": "no", "file_readable": "maybe", "status": 123},
            "summary": {"message": 1, "errors": 2},
            "metadata": {"processed_by": 5, "version": 6, "timestamp": "not-a-date"}
        }
    }

    sd = StandardizedDataValidator(payload)
    res = sd.validate()
    assert res["validation_passed"] is False
    # Expect several schema errors
    assert len(res["schema_errors"]) >= 1
