"""
FastAPI service for RAG Validation System.
Provides Swagger UI for file validation and standardized payload validation.
"""

from typing import Optional, Dict, Any, Union
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field

from .validator import DataValidator, StandardizedDataValidator
from .utils import write_json, write_log
from .langgraph_validator import validate_with_langgraph


class BasePayloadModel(BaseModel):
    class Config:
        extra = "ignore"


class FileDetails(BasePayloadModel):
    file_path: str = Field(..., example="data/raw/sample.txt")
    file_type: str = Field(..., example="text")
    created_at: str = Field(..., example="2026-04-10 12:45:00")


class ValidationPayload(BasePayloadModel):
    file_exists: bool = Field(..., example=True)
    file_not_empty: bool = Field(..., example=True)
    file_readable: bool = Field(..., example=True)
    status: str = Field(..., example="SUCCESS")


class SummaryPayload(BasePayloadModel):
    message: str = Field(..., example="Validation completed successfully")
    errors: Optional[str] = Field(None, example=None)


class MetadataPayload(BasePayloadModel):
    processed_by: str = Field(..., example="RAG Validation System")
    version: str = Field(..., example="1.0")
    timestamp: str = Field(..., example="2026-04-10 12:45:00")


class StandardizedData(BasePayloadModel):
    file_details: FileDetails
    validation: ValidationPayload
    summary: SummaryPayload
    metadata: MetadataPayload


class StandardizedPayload(BasePayloadModel):
    document_id: str = Field(..., example="DOC001")
    standardized_data: StandardizedData


class PayloadWrapper(BasePayloadModel):
    payload: StandardizedPayload


class FileValidationRequest(BasePayloadModel):
    file_path: str = Field(..., example="data/raw/sample.txt")
    document_id: Optional[str] = Field(None, example="DOC001")
    save_output: Optional[bool] = Field(False, example=True)
    output_path: Optional[str] = Field(None, example="outputs/DOC001.json")

# Request-side models for enterprise input schema
class RequestFileDetails(BasePayloadModel):
    file_name: str = Field(..., example="invoice_001.pdf")
    file_path: str = Field(..., example="data/raw/invoice_001.pdf")
    file_type: str = Field(..., example="pdf")
    file_size_kb: int = Field(..., example=245)


class RequestCustomerDetails(BasePayloadModel):
    customer_id: str = Field(..., example="CUST1001")
    customer_name: str = Field(..., example="ABC Technologies")
    customer_email: str = Field(..., example="abc@example.com")


class ValidateRequest(BasePayloadModel):
    """Enterprise-level input schema for validation requests.

    Clients send metadata and file details; the server returns the
    `standardized_data` including validation_result, summary, and metadata.
    """
    document_id: str = Field(..., example="DOC001")
    document_type: str = Field(..., example="invoice")
    source_system: str = Field(..., example="ERP_System")
    uploaded_by: str = Field(..., example="Kishore")
    uploaded_at: str = Field(..., example="2026-05-12T10:30:00")
    file_details: RequestFileDetails
    customer_details: RequestCustomerDetails
    save_output: Optional[bool] = Field(False, example=True)
    output_path: Optional[str] = Field(None, example="outputs/DOC001.json")


class LangGraphValidateRequest(BasePayloadModel):
    input_json: Dict[str, Any] = Field(..., description="The input JSON to validate and process")


app = FastAPI(
    title="RAG Validation API",
    description="API for file validation and standardized payload validation.",
    version="1.0"
)


def _resolve_payload(request: ValidateRequest) -> Dict[str, Any]:
    """Resolve a validate request into a standardized result by
    extracting the file path from `file_details` and delegating to
    `DataValidator`.
    """
    file_path = None
    document_id = None

    # Support both new enterprise request and older minimal request shapes
    if hasattr(request, "file_details") and request.file_details:
        file_path = request.file_details.file_path
        document_id = request.document_id
    elif getattr(request, "file_path", None):
        file_path = request.file_path
        document_id = request.document_id

    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required to validate payload")

    validator = DataValidator(file_path, document_id)
    return validator.validate()


def _maybe_save_output(result: Dict[str, Any], save_output: bool, output_path: Optional[str]) -> None:
    if not save_output:
        return

    path = output_path or f"outputs/{result.get('document_id', 'result')}.json"
    write_json(path, result)
    write_log(f"Saved API result to {path}")


@app.get("/", summary="Service health")
def root() -> Dict[str, str]:
    return {"message": "RAG Validation API is running."}


@app.get("/health", summary="Health check")
def health() -> Dict[str, str]:
    return {"message": "RAG Validation API is running."}


@app.post("/validate-file", response_model=Dict[str, Any], summary="Validate a file path")
def validate_file(request: FileValidationRequest) -> Dict[str, Any]:
    try:
        validator = DataValidator(request.file_path, request.document_id)
        result = validator.validate()
        _maybe_save_output(result, request.save_output, request.output_path)
        return result
    except Exception as e:
        write_log(f"API file validation failed: {str(e)}", "error")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/validate-payload", response_model=Dict[str, Any], summary="Validate a payload by file path")
def validate_payload(request_body: Dict[str, Any] = Body(
    ...,
    example={
        "document_id": "DOC001",
        "document_type": "invoice",
        "source_system": "ERP_System",
        "uploaded_by": "Kishore",
        "uploaded_at": "2026-05-12T10:30:00",
        "file_details": {
            "file_name": "invoice_001.pdf",
            "file_path": "data/raw/invoice_001.pdf",
            "file_type": "pdf",
            "file_size_kb": 245
        },
        "customer_details": {
            "customer_id": "CUST1001",
            "customer_name": "ABC Technologies",
            "customer_email": "abc@example.com"
        }
    }
)) -> Dict[str, Any]:
    """Accept multiple payload shapes and return the generated standardized validation result.

    Supported shapes:
    - Enterprise `file_details` nested schema
    - Minimal `{file_path, document_id}` shape
    - Legacy standardized payload containing `standardized_data`
    """
    try:
        save_output = request_body.get("save_output", False)
        output_path = request_body.get("output_path")

        # 1) Standardized (legacy) payload posted directly
        if isinstance(request_body.get("standardized_data"), dict):
            validator = StandardizedDataValidator(request_body)
            result = validator.validate()
            _maybe_save_output(result, save_output, output_path)
            return result

        # 2) Enterprise nested schema
        if isinstance(request_body.get("file_details"), dict) and request_body["file_details"].get("file_path"):
            file_path = request_body["file_details"]["file_path"]
            document_id = request_body.get("document_id")
            validator = DataValidator(file_path, document_id)
            result = validator.validate()
            _maybe_save_output(result, save_output, output_path)
            return result

        # 3) Minimal shape with top-level file_path
        if request_body.get("file_path"):
            validator = DataValidator(request_body["file_path"], request_body.get("document_id"))
            result = validator.validate()
            _maybe_save_output(result, save_output, output_path)
            return result

        raise HTTPException(status_code=400, detail="file_path is required to validate payload")
    except HTTPException:
        raise
    except Exception as e:
        write_log(f"API payload validation failed: {str(e)}", "error")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/validate", response_model=Dict[str, Any], summary="Validate either a file or a standardized payload")
def validate(request_body: Dict[str, Any] = Body(
    ...,
    example={
        "document_id": "DOC001",
        "document_type": "invoice",
        "source_system": "ERP_System",
        "uploaded_by": "Kishore",
        "uploaded_at": "2026-05-12T10:30:00",
        "file_details": {
            "file_name": "invoice_001.pdf",
            "file_path": "data/raw/invoice_001.pdf",
            "file_type": "pdf",
            "file_size_kb": 245
        },
        "customer_details": {
            "customer_id": "CUST1001",
            "customer_name": "ABC Technologies",
            "customer_email": "abc@example.com"
        }
    }
)) -> Dict[str, Any]:
    """Accept multiple request shapes:
    - enterprise request (contains `file_details`)
    - legacy file request (top-level `file_path`)
    - wrapper or standardized payload (contains `payload` or `standardized_data`)
    """
    try:
        # Save flags may be present in various shapes
        save_output = request_body.get("save_output", False)
        output_path = request_body.get("output_path")

        # 1) Enterprise shape
        if isinstance(request_body.get("file_details"), dict) and request_body["file_details"].get("file_path"):
            file_path = request_body["file_details"]["file_path"]
            document_id = request_body.get("document_id")
            validator = DataValidator(file_path, document_id)
            result = validator.validate()
            _maybe_save_output(result, save_output, output_path)
            return result

        # 2) Legacy simple file request
        if request_body.get("file_path"):
            validator = DataValidator(request_body["file_path"], request_body.get("document_id"))
            result = validator.validate()
            _maybe_save_output(result, save_output, output_path)
            return result

        # 3) Wrapper or standardized payload posted directly
        if request_body.get("payload"):
            payload = request_body.get("payload")
            # if wrapper contains inner payload object
            if isinstance(payload, dict) and payload.get("payload"):
                payload = payload.get("payload")
            validator = StandardizedDataValidator(payload)
            result = validator.validate()
            _maybe_save_output(result, save_output, output_path)
            return result

        if request_body.get("standardized_data"):
            validator = StandardizedDataValidator(request_body)
            result = validator.validate()
            _maybe_save_output(result, save_output, output_path)
            return result

        raise HTTPException(status_code=400, detail="Unsupported request body shape for /validate")
    except HTTPException:
        raise
    except Exception as e:
        write_log(f"API validate failed: {str(e)}", "error")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/validate-langgraph", response_model=Dict[str, Any], summary="Validate input JSON using LangGraph and GPT-4")
def validate_with_langgraph_endpoint(request: LangGraphValidateRequest = Body(
    ...,
    example={"input_json": {"file_path": "data/raw/sample.txt", "file_type": "text", "created_at": "2026-04-10 12:45:00"}}
)) -> Dict[str, Any]:
    try:
        result = validate_with_langgraph(request.input_json)
        return result
    except Exception as e:
        write_log(f"LangGraph validation failed: {str(e)}", "error")
        raise HTTPException(status_code=400, detail=str(e))

