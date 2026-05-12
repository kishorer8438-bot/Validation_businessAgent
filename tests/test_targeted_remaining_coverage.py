import json
import runpy
import runpy
import builtins
import pytest

from src.validator import DataValidator, StandardizedDataValidator
from src.business_agent import BusinessRulesAgent
from src.utils import FileOperationError, ValidationError


def test_data_validator_init_unexpected_exception_raises_fileoperationerror(monkeypatch, tmp_path):
    # make validate_file_path raise unexpected exception to hit generic except
    monkeypatch.setattr('src.validator.validate_file_path', lambda p: (_ for _ in ()).throw(Exception('boom')))
    with pytest.raises(FileOperationError):
        DataValidator(str(tmp_path / "nope.txt"))


def test_get_file_type_handles_open_exception_returns_unknown(monkeypatch, tmp_path):
    p = tmp_path / "test.bin"
    p.write_bytes(b"garbage")

    # cause open(..., 'rb') to raise when _get_file_type attempts to read header
    real_open = builtins.open

    def fake_open(path, mode='r', *args, **kwargs):
        if 'b' in mode:
            raise Exception('read fail')
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, 'open', fake_open)
    dv = DataValidator(str(p))
    assert dv._get_file_type() == 'unknown'


def test_check_file_not_empty_handles_get_file_info_exception_returns_false(monkeypatch, tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("data")
    dv = DataValidator(str(p))
    monkeypatch.setattr(dv, '_get_file_info', lambda: (_ for _ in ()).throw(Exception('boom')))
    assert dv.check_file_not_empty() is False


def test_check_file_readable_unexpected_exception_returns_false(monkeypatch, tmp_path):
    p = tmp_path / "r.txt"
    p.write_text("hi")
    dv = DataValidator(str(p))
    # force check_file_exists to return True so code reaches open call
    monkeypatch.setattr(dv, 'check_file_exists', lambda: True)

    def fake_open(*args, **kwargs):
        raise ValueError('weird')

    monkeypatch.setattr(builtins, 'open', fake_open)
    assert dv.check_file_readable() is False


def test_standardized_parse_payload_invalid_json_raises():
    with pytest.raises(ValidationError):
        StandardizedDataValidator("not a json string")


def test_standardized_parse_payload_non_dict_raises():
    with pytest.raises(ValidationError):
        StandardizedDataValidator(123)


def test_standardized_parse_datetime_non_string_adds_error():
    payload = {
        "document_id": "D1",
        "standardized_data": {
            "file_details": {"file_path": "p", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "SUCCESS"},
            "summary": {"message": "ok", "errors": None},
            "metadata": {"processed_by": "x", "version": "1.0", "timestamp": "2020-01-01 00:00:00"}
        }
    }
    sv = StandardizedDataValidator(payload)
    sv._parse_datetime(12345, "metadata.timestamp")
    assert any('metadata.timestamp' in e for e in sv.errors)


def test_standardized_validator_validate_handles_validationerror(monkeypatch):
    payload = {"document_id": "D1", "standardized_data": {}}
    sv = StandardizedDataValidator(payload)
    monkeypatch.setattr(sv, '_validate_schema', lambda: (_ for _ in ()).throw(ValidationError('boom')))
    result = sv.validate()
    assert result['validation_passed'] is False
    assert any('boom' in e for e in result['schema_errors'])


def test_business_agent_required_structure_early_return_on_missing_keys():
    payload = {"document_id": "D1", "standardized_data": {"file_details": {}, "validation": {}, "summary": {}, "metadata": {}}}
    agent = BusinessRulesAgent(payload)
    res = agent.validate()
    assert res['business_rule_violations'] != []


def test_business_agent_summary_field_type_violations():
    payload = {
        "document_id": "D1",
        "standardized_data": {
            "file_details": {"file_path": "p", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": "SUCCESS"},
            "summary": {"message": 123, "errors": [1,2,3]},
            "metadata": {"processed_by": "x", "version": "1.0", "timestamp": "2020-01-01 00:00:00"}
        }
    }
    agent = BusinessRulesAgent(payload)
    res = agent.validate()
    assert any('summary.message' in v or 'summary.errors' in v for v in res['business_rule_violations'])


def test_business_agent_check_validation_types_status_non_string():
    payload = {
        "document_id": "D1",
        "standardized_data": {
            "file_details": {"file_path": "p", "file_type": "text", "created_at": "2020-01-01 00:00:00"},
            "validation": {"file_exists": True, "file_not_empty": True, "file_readable": True, "status": 123},
            "summary": {"message": "ok", "errors": None},
            "metadata": {"processed_by": "x", "version": "1.0", "timestamp": "2020-01-01 00:00:00"}
        }
    }
    agent = BusinessRulesAgent(payload)
    res = agent.validate()
    assert any('validation.status must be a string' in v for v in res['business_rule_violations'])


def test_business_agent_validate_handles_validationerror(monkeypatch):
    payload = {"document_id": "D1", "standardized_data": {}}
    agent = BusinessRulesAgent(payload)
    monkeypatch.setattr(agent, '_validate_required_structure', lambda: (_ for _ in ()).throw(ValidationError('boom')))
    res = agent.validate()
    assert res['validation_passed'] is False
    assert any('boom' in v for v in res['business_rule_violations'])


def test_validator_main_guard_executes_and_exits(monkeypatch, tmp_path):
    # Execute the actual __main__ block from src/validator.py with line numbers preserved
    from pathlib import Path
    import src.validator as validator_mod
    src_text = Path('src/validator.py').read_text().splitlines()
    start_idx = None
    for i, ln in enumerate(src_text):
        if ln.strip().startswith('if __name__'):
            start_idx = i
            break
    assert start_idx is not None
    block = '\n'.join(src_text[start_idx:])

    # Patch DataValidator.validate to raise so the except block runs and calls sys.exit(1)
    monkeypatch.setattr(validator_mod.DataValidator, 'validate', lambda self: (_ for _ in ()).throw(Exception('boom')))

    code = '\n' * start_idx + block
    globs = {'__name__': '__main__', 'DataValidator': validator_mod.DataValidator, 'sys': __import__('sys')}
    with pytest.raises(SystemExit):
        exec(compile(code, 'src/validator.py', 'exec'), globs)


def test_get_file_type_detects_pdf_header(tmp_path):
    p = tmp_path / "sample.bin"
    p.write_bytes(b"%PDF-1.4\n1 0 obj\n")
    dv = DataValidator(str(p))
    assert dv._get_file_type() == 'pdf'


def test_check_file_not_empty_exception_path(monkeypatch, tmp_path):
    p = tmp_path / "f2.txt"
    p.write_text("x")
    dv = DataValidator(str(p))
    # Force existence check to pass so _get_file_info is called inside check_file_not_empty
    monkeypatch.setattr(dv, 'check_file_exists', lambda: True)
    monkeypatch.setattr(dv, '_get_file_info', lambda: (_ for _ in ()).throw(Exception('boom')))
    assert dv.check_file_not_empty() is False


def test_main_prints_validator_json(monkeypatch, capsys):
    import src.validator as validator_mod
    from pathlib import Path

    # Patch validate and to_json to return controlled values so print() runs
    monkeypatch.setattr(validator_mod.DataValidator, 'validate', lambda self: {"ok": True})
    monkeypatch.setattr(validator_mod.DataValidator, 'to_json', lambda self: '{"ok": true}')

    src_text = Path('src/validator.py').read_text().splitlines()
    start_idx = None
    for i, ln in enumerate(src_text):
        if ln.strip().startswith('if __name__'):
            start_idx = i
            break
    assert start_idx is not None
    block = '\n'.join(src_text[start_idx:])
    code = '\n' * start_idx + block

    globs = {'__name__': '__main__', 'DataValidator': validator_mod.DataValidator}
    exec(compile(code, 'src/validator.py', 'exec'), globs)
    captured = capsys.readouterr()
    assert '{"ok": true}' in captured.out


def test_business_agent_validate_required_structure_early_return():
    payload = {"document_id": "D1", "standardized_data": {}}
    agent = BusinessRulesAgent(payload)
    # Directly invoke the internal checker to exercise the early return at the standardized check
    agent._validate_required_structure()
    assert any("Missing required key" in v for v in agent.violations)
