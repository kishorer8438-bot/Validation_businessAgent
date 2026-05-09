"""
FastAPI service for RAG Validation System.
Provides Swagger UI for file validation and standardized payload validation.
"""

from typing import Optional, Dict, Any, Union
from fastapi import FastAPI, HTTPException
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


class ValidateRequest(BasePayloadModel):
    file_path: Optional[str] = Field(None, example="data/raw/sample.txt")
    document_id: Optional[str] = Field(None, example="DOC001")
    save_output: Optional[bool] = Field(False, example=True)
    output_path: Optional[str] = Field(None, example="outputs/DOC001.json")
    standardized_data: Optional[StandardizedData] = None
    payload: Optional[PayloadWrapper] = None


class LangGraphValidateRequest(BasePayloadModel):
    input_json: Dict[str, Any] = Field(..., description="The input JSON to validate and process")


app = FastAPI(
    title="RAG Validation API",
    description="API for file validation and standardized payload validation.",
    version="1.0"
)


def _resolve_payload(request: ValidateRequest) -> Dict[str, Any]:
    if request.payload is not None:
        return request.payload.payload.dict()

    if request.standardized_data is not None:
        return {
            "document_id": request.document_id or "UNKNOWN",
            "standardized_data": request.standardized_data.dict()
        }

    raise HTTPException(status_code=400, detail="Standardized payload is required when file_path is missing")


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


@app.post("/validate-payload", response_model=Dict[str, Any], summary="Validate a standardized payload")
def validate_payload(request_body: Union[StandardizedPayload, PayloadWrapper]) -> Dict[str, Any]:
    try:
        payload = request_body.payload.dict() if isinstance(request_body, PayloadWrapper) else request_body.dict()
        validator = StandardizedDataValidator(payload)
        return validator.validate()
    except Exception as e:
        write_log(f"API payload validation failed: {str(e)}", "error")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/validate", response_model=Dict[str, Any], summary="Validate either a file or a standardized payload")
def validate(request: ValidateRequest) -> Dict[str, Any]:
    try:
        if request.file_path:
            validator = DataValidator(request.file_path, request.document_id)
            result = validator.validate()
        else:
            payload = _resolve_payload(request)
            validator = StandardizedDataValidator(payload)
            result = validator.validate()

        _maybe_save_output(result, request.save_output, request.output_path)
        return result
    except HTTPException:
        raise
    except Exception as e:
        write_log(f"API validate failed: {str(e)}", "error")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/validate-langgraph", response_model=Dict[str, Any], summary="Validate input JSON using LangGraph and GPT-4")
def validate_with_langgraph_endpoint(request: LangGraphValidateRequest) -> Dict[str, Any]:
    try:
        result = validate_with_langgraph(request.input_json)
        return result
    except Exception as e:
        write_log(f"LangGraph validation failed: {str(e)}", "error")
        raise HTTPException(status_code=400, detail=str(e))

