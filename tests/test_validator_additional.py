import json
import pytest
from pathlib import Path

from src.validator import DataValidator, StandardizedDataValidator


def test_data_validator_success_and_fields(tmp_path):
    p = tmp_path / "sample.txt"
    p.write_text("some content\nline2")

    dv = DataValidator(str(p), "DOCTEST")
    res = dv.validate()
    std = res["standardized_data"]
    assert std["validation"]["status"] == "SUCCESS"
    assert std["file_details"]["file_path"].endswith("sample.txt")


def test_data_validator_empty_file_reports_empty(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_text("")

    dv = DataValidator(str(p), "DOCEMPTY")
    res = dv.validate()
    assert res["standardized_data"]["validation"]["status"] == "EMPTY_FILE"


def test_data_validator_unknown_type(tmp_path):
    p = tmp_path / "weird.xyz"
    p.write_text("no signature here")
    dv = DataValidator(str(p), "DOCXYZ")
    res = dv.validate()
    ftype = res["standardized_data"]["file_details"]["file_type"]
    assert ftype in ("unknown", "text", "json")


def test_standardized_validator_fails_on_missing_keys():
    payload = {"document_id": "X"}  # missing standardized_data
    sdv = StandardizedDataValidator(payload)
    res = sdv.validate()
    assert res["validation_passed"] is False
    assert len(res["schema_errors"]) > 0


def test_standardized_validator_success_roundtrip(tmp_path):
    # use DataValidator to produce a valid standardized_data
    p = tmp_path / "s.txt"
    p.write_text("hello world")
    dv = DataValidator(str(p), "DOCRT")
    raw = dv.validate()

    payload = {"document_id": raw["document_id"], "standardized_data": raw["standardized_data"]}
    sdv = StandardizedDataValidator(payload)
    res = sdv.validate()
    assert res["validation_passed"] is True
