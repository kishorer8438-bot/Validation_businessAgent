import json
from pathlib import Path
import pytest

from src.main import (
    setup_cli_parser, ValidationConfig, validate_single_file,
    validate_payload_file, validate_batch, save_results
)


def test_setup_cli_parser_has_expected_args():
    parser = setup_cli_parser()
    args = parser.parse_args(["file.txt", "--verbose", "--batch"])  # basic parse
    assert args.file_path == "file.txt"
    assert args.verbose is True


def test_validation_config_load(tmp_path):
    cfgfile = tmp_path / "cfg.json"
    cfgfile.write_text(json.dumps({"default_output_dir": "myout", "verbose": True}))
    cfg = ValidationConfig(str(cfgfile))
    # load_config executed in __init__ if file exists
    assert hasattr(cfg, "default_output_dir")


def test_validate_single_file_invalid_path_returns_error():
    cfg = ValidationConfig(None)
    res = validate_single_file("", cfg)
    assert isinstance(res, dict)
    assert "error" in res


def test_validate_payload_file_invalid_path_returns_standardized_error():
    res = validate_payload_file("does_not_exist.json")
    assert isinstance(res, dict)
    assert res.get("validation_passed") is False or res.get("source") == "standardized_payload"


def test_validate_batch_empty_list_returns_empty(cfg=None):
    cfg = ValidationConfig(None)
    results = validate_batch([], cfg)
    assert results == []


def test_save_results_single_and_batch(tmp_path):
    cfg = ValidationConfig(None)
    r1 = {"document_id": "A", "standardized_data": {"validation": {"status": "SUCCESS"}}}
    outdir = tmp_path / "outdir"
    # single result saved to dir
    save_results([r1], str(outdir), cfg)
    files = list(outdir.glob("*.json"))
    assert any(f.name.startswith("A") for f in files)

    # batch save to file
    outfile = tmp_path / "batch.json"
    save_results([r1, r1], str(outfile), cfg)
    assert outfile.exists()
