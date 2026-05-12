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
    file_type: Optional[str] = Field(None, example="text")
    created_at: Optional[str] = Field(None, example="2026-04-10 12:45:00")


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


class MinimalRequest(BasePayloadModel):
    document_id: Optional[str] = Field(None, example="DOC001")
    file_path: Optional[str] = Field(None, example="data/raw/sample.txt")


class LangGraphValidateRequest(BasePayloadModel):
    input_json: Dict[str, Any] = Field(..., description="The input JSON to validate and process")


app = FastAPI(
    title="RAG Validation API",
    description="API for file validation and standardized payload validation.",
    version="1.0"
)


def _build_response_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    # Ensure response matches the StandardizedPayload shape
    return {
        "document_id": result.get("document_id", "UNKNOWN"),
        "standardized_data": result.get("standardized_data", result)
    }


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


@app.post("/validate-file", response_model=StandardizedPayload, summary="Validate a file path")
def validate_file(request: FileValidationRequest, save_output: bool = False, output_path: Optional[str] = None) -> Dict[str, Any]:
    try:
        validator = DataValidator(request.file_path, request.document_id)
        result = validator.validate()
        _maybe_save_output(result, save_output, output_path)
        return _build_response_payload(result)
    except Exception as e:
        write_log(f"API file validation failed: {str(e)}", "error")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/validate-payload", response_model=StandardizedPayload, summary="Validate a file using minimal payload")
def validate_payload(request_body: MinimalRequest, save_output: bool = False, output_path: Optional[str] = None) -> Dict[str, Any]:
    try:
        if not request_body.file_path:
            raise HTTPException(status_code=400, detail="file_path is required for payload validation")

        validator = DataValidator(request_body.file_path, request_body.document_id)
        result = validator.validate()
        _maybe_save_output(result, save_output, output_path)
        return _build_response_payload(result)
    except Exception as e:
        write_log(f"API payload validation failed: {str(e)}", "error")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/validate", response_model=StandardizedPayload, summary="Validate a file by minimal request")
def validate(request: MinimalRequest, save_output: bool = False, output_path: Optional[str] = None) -> Dict[str, Any]:
    try:
        if not request.file_path:
            raise HTTPException(status_code=400, detail="file_path is required")

        validator = DataValidator(request.file_path, request.document_id)
        result = validator.validate()
        _maybe_save_output(result, save_output, output_path)
        return _build_response_payload(result)
    except HTTPException:
        raise
    except Exception as e:
        write_log(f"API validate failed: {str(e)}", "error")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/validate-langgraph", response_model=StandardizedPayload, summary="Validate input JSON using LangGraph and GPT-4")
def validate_with_langgraph_endpoint(request: LangGraphValidateRequest) -> Dict[str, Any]:
    try:
        result = validate_with_langgraph(request.input_json)
        return _build_response_payload(result)
    except Exception as e:
        write_log(f"LangGraph validation failed: {str(e)}", "error")
        raise HTTPException(status_code=400, detail=str(e))

