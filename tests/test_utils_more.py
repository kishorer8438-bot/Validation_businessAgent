import json
from pathlib import Path
import os

import pytest

from src import utils


def test_create_directory_empty_path():
    assert utils.create_directory("") is False


def test_write_json_and_backup_and_read_json(tmp_path):
    p = tmp_path / "data"
    file_path = p / "test.json"

    # initial write
    utils.write_json(file_path, {"a": 1})
    assert file_path.exists()

    # overwrite with backup
    utils.write_json(file_path, {"b": 2}, create_backup=True)
    backup = file_path.with_suffix(file_path.suffix + utils.BACKUP_SUFFIX)
    assert backup.exists()

    # read back
    data = utils.read_json(file_path)
    assert data == {"b": 2}


def test_read_json_invalid_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ this is not: valid json }")

    with pytest.raises(utils.FileOperationError):
        utils.read_json(p)


def test_safe_delete_and_append(tmp_path):
    p = tmp_path / "does_not_exist.txt"
    # deleting non-existent should return True
    assert utils.safe_delete(p) is True

    # append_file should create and append
    f = tmp_path / "append.txt"
    utils.append_file(str(f), "line1")
    utils.append_file(str(f), "line2")
    content = f.read_text()
    assert "line1" in content and "line2" in content


def test_list_files_not_directory_raises(tmp_path):
    f = tmp_path / "afile.txt"
    f.write_text("hi")

    with pytest.raises(utils.FileOperationError):
        utils.list_files(f, "*")


def test_write_file_create_backup(tmp_path):
    f = tmp_path / "orig.txt"
    f.write_text("original")

    # now overwrite using write_file with backup
    utils.write_file(f, "newcontent", create_backup=True)
    backup = f.with_suffix(f.suffix + utils.BACKUP_SUFFIX)
    assert backup.exists()
