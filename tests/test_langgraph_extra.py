import json
import types

import pytest

from src import langgraph_validator as lg


class FakeLLM:
    def __init__(self, *args, **kwargs):
        pass

    def invoke(self, prompt):
        # simple object with content attribute used in module
        o = types.SimpleNamespace()
        # return minimal valid JSON content for generate_output_node
        o.content = json.dumps({
            "document_id": "DOC_FAKE",
            "standardized_data": {
                "validation": {"status": "SUCCESS"}
            }
        })
        return o


class FakeApp:
    def __init__(self, result):
        self._result = result

    def invoke(self, state):
        return {"output_json": self._result}


class FakeStateGraph:
    def __init__(self, _):
        pass

    def add_node(self, *_):
        return None

    def add_edge(self, *_):
        return None

    def set_entry_point(self, *_):
        return None

    def compile(self):
        return FakeApp(lg.example_output)


def test_validate_with_langgraph_monkeypatched(monkeypatch):
    # Monkeypatch the ChatGoogleGenerativeAI and StateGraph used inside function
    monkeypatch.setattr(lg, "ChatGoogleGenerativeAI", FakeLLM)
    monkeypatch.setattr(lg, "StateGraph", FakeStateGraph)

    input_data = {"file_path": "data/raw/sample.txt"}
    result = lg.validate_with_langgraph(input_data)
    assert isinstance(result, dict)
    assert result.get("standardized_data") is not None


def test_generate_output_node_fallback_json():
    # Ensure generate_output_node handles non-json content gracefully
    state = {"input_json": {"file_path": "x"}, "validation_result": "bad json", "output_json": {}}
    # Simulate content that is not JSON
    def fake_invoke(prompt):
        o = types.SimpleNamespace()
        o.content = "not a json"
        return o

    monkey = pytest.MonkeyPatch()
    monkey.setattr(lg, "llm", types.SimpleNamespace(invoke=fake_invoke), raising=False)
    try:
        out = lg.generate_output_node(state)
        assert "output_json" in out
    finally:
        monkey.undo()
