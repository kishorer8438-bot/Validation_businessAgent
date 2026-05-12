from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code in [200, 404]


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200


def test_docs_endpoint():
    response = client.get("/docs")
    assert response.status_code == 200


def test_validate_file_success():
    payload = {"file_path": "data/raw/sample.txt"}
    resp = client.post("/validate-file", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "standardized_data" in body
    assert body["standardized_data"]["validation"]["status"] == "SUCCESS"


def test_validate_file_not_found():
    payload = {"file_path": "data/raw/does_not_exist.txt"}
    resp = client.post("/validate-file", json=payload)
    # API returns a standardized result even when file is missing
    assert resp.status_code == 200
    body = resp.json()
    assert body["standardized_data"]["validation"]["status"] == "FILE_NOT_FOUND"


def test_validate_payload_success():
    # load sample payload from repo
    import json
    with open("data/payload.json", "r", encoding="utf-8") as f:
        payload = json.load(f)

    # The API now expects a minimal request (file_path + document_id);
    # use the file_path from the sample payload to request validation.
    file_path = payload.get("standardized_data", {}).get("file_details", {}).get("file_path")
    resp = client.post("/validate-payload", json={"file_path": file_path, "document_id": payload.get("document_id")})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("standardized_data", {}).get("validation", {}).get("status") == "SUCCESS"


def test_validate_endpoint_with_file_and_payload():
    # file path variation
    resp1 = client.post("/validate", json={"file_path": "data/raw/sample.txt"})
    assert resp1.status_code == 200
    assert resp1.json()["standardized_data"]["validation"]["status"] == "SUCCESS"

    # payload variation: request the same validation via minimal payload
    import json
    with open("data/payload.json", "r", encoding="utf-8") as f:
        payload = json.load(f)

    file_path = payload.get("standardized_data", {}).get("file_details", {}).get("file_path")
    resp2 = client.post("/validate", json={"file_path": file_path, "document_id": payload.get("document_id")})
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2.get("standardized_data", {}).get("validation", {}).get("status") == "SUCCESS"


def test_validate_langgraph_endpoint_monkeypatched(monkeypatch):
    # Replace the heavy langgraph function with a deterministic stub
    from src import api

    def fake_validate_with_langgraph(input_json):
        return {"document_id": "FAKE", "standardized_data": {"validation": {"status": "SUCCESS"}}}

    monkeypatch.setattr(api, "validate_with_langgraph", fake_validate_with_langgraph)

    resp = client.post("/validate-langgraph", json={"input_json": {"file_path": "data/raw/sample.txt"}})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("document_id") == "FAKE"


def test_main_functions_direct_calls(tmp_path):
    # Import functions directly from src.main to exercise module-level code
    from src import main as main_mod
    from src.main import ValidationConfig
    from pathlib import Path

    cfg = ValidationConfig(None)
    # test validate_single_file
    res = main_mod.validate_single_file("data/raw/sample.txt", cfg)
    assert isinstance(res, dict)
    assert res.get("standardized_data", {}).get("validation", {}).get("status") == "SUCCESS"

    # test validate_payload_file
    payload_res = main_mod.validate_payload_file("data/payload.json")
    assert payload_res.get("validation_passed") is True

    # test validate_batch
    files = [Path("data/raw/sample.txt"), Path("data/raw/test.txt")]
    batch_results = main_mod.validate_batch(files, cfg)
    assert isinstance(batch_results, list)

    # test save_results for a dir path
    outdir = tmp_path / "out"
    main_mod.save_results(batch_results, str(outdir), cfg)
    # Expect files created in outdir
    created = list(outdir.glob("*.json"))
    assert len(created) == len(batch_results)