import json
import pytest
from pathlib import Path

from src import utils


def test_validate_file_path_empty_raises():
    with pytest.raises(utils.ValidationError):
        utils.validate_file_path("")


def test_write_and_read_json_roundtrip(tmp_path):
    data = {"a": 1, "b": "x"}
    path = tmp_path / "data.json"
    utils.write_json(path, data)

    read = utils.read_json(path)
    assert read == data


def test_get_file_info_nonexistent(tmp_path):
    p = tmp_path / "nope.txt"
    info = utils.get_file_info(p)
    assert info["exists"] is False
    assert info["size"] == 0


def test_safe_delete_and_write_file(tmp_path):
    p = tmp_path / "f.txt"
    utils.write_file(p, "hello")
    assert p.exists()
    assert utils.safe_delete(p) is True
    # deleting again should be fine
    assert utils.safe_delete(p) is True
