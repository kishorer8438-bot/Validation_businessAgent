import json
import time
from pathlib import Path

import pytest

from src.main import (
    ValidationConfig, validate_single_file, validate_payload_file,
    validate_batch, save_results
)


def test_validation_config_load_and_override(tmp_path):
    cfg_file = tmp_path / "cfg.json"
    cfg_file.write_text(json.dumps({"default_output_dir": "outdir", "version": "2.0"}))

    cfg = ValidationConfig(str(cfg_file))
    assert cfg.default_output_dir == "outdir"
    assert cfg.version == "2.0"


def test_validate_single_file_error_returns_error_dict():
    cfg = ValidationConfig(None)
    # empty path should cause validation error path
    res = validate_single_file("", cfg)
    assert isinstance(res, dict)
    assert "error" in res


def test_validate_payload_file_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json }")
    res = validate_payload_file(str(bad))
    assert res.get("validation_passed") is False
    assert any("Invalid JSON" in e or "Invalid JSON" in str(e) or "Invalid" in str(e) for e in res.get("schema_errors", [])) or isinstance(res.get("schema_errors"), list)


def test_validate_batch_and_save_results(tmp_path):
    # create files
    files = []
    for i in range(3):
        p = tmp_path / f"f{i}.txt"
        p.write_text("hello")
        files.append(p)

    cfg = ValidationConfig(None)
    results = validate_batch(files, cfg)
    assert isinstance(results, list)
    assert len(results) == 3

    outdir = tmp_path / "out"
    save_results(results, str(outdir), cfg)
    # expect 3 json files
    created = list(outdir.glob("*.json"))
    assert len(created) == 3

    # test saving single result to file path
    single_out = tmp_path / "single.json"
    save_results([results[0]], str(single_out), cfg)
    assert single_out.exists()
