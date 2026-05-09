import json
import os
from pathlib import Path
import pytest

from src import utils


def test_validate_file_path_invalid():
    with pytest.raises(utils.ValidationError):
        utils.validate_file_path("")


def test_read_json_missing_file(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(utils.FileOperationError):
        utils.read_json(str(missing))


def test_write_and_read_json_roundtrip(tmp_path):
    data = {"a": 1, "b": "two"}
    out = tmp_path / "out.json"
    utils.write_json(str(out), data)
    loaded = utils.read_json(str(out))
    assert loaded == data


def test_get_file_info_nonexistent(tmp_path):
    p = tmp_path / "missing.txt"
    info = utils.get_file_info(str(p))
    assert info["exists"] is False


def test_get_file_info_and_write_file(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello")
    info = utils.get_file_info(str(p))
    assert info["exists"] is True
    assert info["size"] > 0


def test_create_directory_empty_path_returns_false():
    assert utils.create_directory("") is False


def test_write_log_writes_file(tmp_path):
    logfile = tmp_path / "app.log"
    utils.write_log("test message", log_file=str(logfile))
    assert logfile.exists()
    txt = logfile.read_text(encoding="utf-8")
    assert "test message" in txt
