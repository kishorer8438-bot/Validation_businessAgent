<!--
  README.md — Validation Business Agent
  Polished for enterprise review and portfolio use.
-->

# Validation Business Agent 🧾

Enterprise-ready invoice validation microservice.

This project validates invoice JSON payloads using schema checks and layered business-rule validators, returning structured validation results suitable for automated reconciliation and downstream processing.

---

## 1. Project Overview

- Purpose: Validate invoices for correctness and business compliance before downstream processing.
- Outputs: validation status, score, errors, warnings, and a detailed checks array.
- Audience: integrators, SRE/DevOps, and data-validation teams.

---

## 2. Key Features ✅

- Schema validation (required fields, types)
- Business-rule validation (totals, tax formats, currency rules)
- Extensible validator chain (plug new rules easily)
- FastAPI-based HTTP API for synchronous validation
- Audit-ready JSON output and optional persistence
- Comprehensive test suite with full coverage (165 tests, 100%)

---

## 3. Tech Stack 🧰

- Python 3.10+
- FastAPI (HTTP API)
- Pytest (testing)
- PlantUML (architecture diagram)
- Optional: Uvicorn for local serving

---

## 4. Project Architecture 📐

High level components:

- API (FastAPI): receives payloads and returns results.
- Validation Agent: orchestrates validators and aggregates results.
- Validators: schema validator, business-rule validators, optional AI/third-party validators.
- Response Formatter: normalizes results into a standard output shape.

Sequence (see diagram below): Client -> API -> Validation Agent -> Validators -> Aggregator -> API -> Client

---

## 5. Installation Guide 🛠️

Clone and prepare the environment:

```bash
git clone https://github.com/kishore8438r-eng/Validation_BusinessAgent.git
cd Validation_BusinessAgent
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -r requirements.txt
```

Run locally (development):

```bash
uvicorn src.main:app --reload --port 8000
```

Open API docs: http://localhost:8000/docs

---

## 6. API Usage 🚀

POST /validate

- Description: Validate an invoice JSON payload.
- Content-Type: `application/json`

Example (curl):

```bash
curl -s -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d @sample_input.json
```

GET /health — liveness/readiness probe

---

## 7. Validation Workflow 🔍

1. Ingestion: API receives payload and performs basic sanitation.
2. Schema Validation: required fields and types are checked; failures return early with details.
3. Business Rules: Validators check totals, tax IDs, currencies, thresholds, and organization-specific rules.
4. Aggregation: Results are tagged with severity (error/warning/info), a validity flag, and a summary score.
5. Response: normalized JSON with `valid`, `summary`, `checks`, and a timestamp.

Design principles: fail-fast on schema errors, clear remediation messages, and modular validators for extensibility.

---

## 8. Sample Input 📥

Save the example below as `sample_input.json` for local testing.

```json
{
  "invoice_id": "INV-2026-0001",
  "date": "2026-05-01",
  "supplier": {"name": "Acme Supplies Ltd.", "tax_id": "GB123456789"},
  "buyer": {"name": "Contoso Ltd.", "tax_id": "GB987654321"},
  "items": [
    {"description": "Widget A", "quantity": 10, "unit_price": 19.99, "currency": "USD"},
    {"description": "Widget B", "quantity": 5, "unit_price": 49.50, "currency": "USD"}
  ],
  "total_amount": 399.40,
  "metadata": {"origin": "EDI", "received_at": "2026-05-02T10:15:30Z"}
}
```

---

## 9. Sample Output 📤

Typical response produced by the service:

```json
{
  "document_id": "INV-2026-0001",
  "validation_status": "SUCCESS",
  "validation_result": {
    "is_valid": true,
    "validation_score": 1,
    "errors": [],
    "warnings": []
  },
  "processed_timestamp": "2026-05-13T08:45:59.331717"
}
```

---

## 10. UML Sequence Diagram 📈

High-level flow (PlantUML):

![UML Sequence Diagram](https://www.plantuml.com/plantuml/svg/RPB1ReCm44Jl-nMht57l7AfG0XLLbKH1wTs25RNg69UrA_NlkuO4GjG3Ckmy3JChRzchmOUBmGzbTAkyxkrEgsvG5m3L-7x0CzC0u0JJZNRAUjoKYdrsh52U3IgEvnfOp33hoFg9Yc__SlANmdRQqiZDmpNx4bW8PZm5G_Ty_EOrUo9slMN2Lx8qHA-9l8u1OYbCdcDoJB4css9bVthT4BxLXpt4UPHZP06kaKWSlWEnXqaGOccGOlv9pHUMcapBi0X2ZH65o9mplxXgmZ29oOFPtGebTZ3-mV7MCBrr93m4xuA7MKhcWh7Jqdui9zgu16b_plEYhl49ownwBtO0Mzc7t8a_)

Source: [diagram.puml](diagram.puml)

---

## 11. Testing & Coverage 🧪

- Test runner: `pytest`
- Current status: **165 tests passed** ✅
- Coverage: **100%** across core modules

Run tests locally:

```bash
pytest -q
coverage run -m pytest && coverage report -m
```

CI integration: include these commands in your pipeline to fail on regressions.

---

## 12. Future Enhancements 🔭

- Country-specific VAT and PO/invoice matching plugins
- Support for XML / EDIFACT adapters and file-format adapters
- Asynchronous batch processing (Celery, queueing)
- Authentication, RBAC, and API rate-limiting
- Observability: tracing, structured logs, and metrics

---

## 13. Contributors

* Project Team

---

For changes, follow the guidelines in `CONTRIBUTING.md`.

