"""
Data Validator for RAG Validation System
Provides comprehensive file validation with standardized output format.
"""

import os
import datetime
import json
from typing import Optional, Dict, Any, Union, List
from pathlib import Path

from .business_agent import BusinessRulesAgent
from .utils import (
    write_log, validate_file_path, get_file_info, ValidationError,
    FileOperationError, DEFAULT_ENCODING
)

# Standardized payload schema keys
FILE_DETAILS_KEYS = ["file_path", "file_type", "created_at"]
VALIDATION_KEYS = ["file_exists", "file_not_empty", "file_readable", "status"]
SUMMARY_KEYS = ["message", "errors"]
METADATA_KEYS = ["processed_by", "version", "timestamp"]
DATETIME_FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]


class DataValidator:
    """
    Comprehensive file validator for RAG system.

    Provides standardized validation results with detailed metadata,
    error handling, and logging capabilities.
    """

    # Supported file types and their extensions
    SUPPORTED_TYPES = {
        'text': ['.txt', '.md', '.rst'],
        'pdf': ['.pdf'],
        'word': ['.doc', '.docx'],
        'excel': ['.xls', '.xlsx', '.csv'],
        'json': ['.json'],
        'xml': ['.xml', '.html', '.htm'],
        'code': ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs'],
        'config': ['.yml', '.yaml', '.ini', '.cfg', '.conf']
    }

    def __init__(self, file_path: Union[str, Path], document_id: Optional[str] = None,
                 system_name: str = "RAG Validation System", version: str = "1.0"):
        """
        Initialize validator with file path and optional parameters.

        Args:
            file_path: Path to file to validate
            document_id: Optional custom document ID
            system_name: Name of processing system
            version: System version
        """
        try:
            self.file_path = str(validate_file_path(file_path))
            self.document_id = document_id or self._generate_document_id()
            self.system_name = system_name
            self.version = version
            self.file_info = None  # Cache file info

            write_log(f"Initialized validator for file: {self.file_path}")

        except ValidationError as e:
            write_log(f"Validation error during initialization: {str(e)}", "error")
            raise
        except Exception as e:
            write_log(f"Unexpected error during initialization: {str(e)}", "error")
            raise FileOperationError(f"Failed to initialize validator: {str(e)}")

    def _generate_document_id(self) -> str:
        """Generate a unique document ID based on timestamp."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"DOC{timestamp}"

    def _get_file_type(self) -> str:
        """
        Infer file type from extension with comprehensive mapping.

        Returns:
            str: File type category
        """
        try:
            path_obj = Path(self.file_path)
            ext = path_obj.suffix.lower()

            for file_type, extensions in self.SUPPORTED_TYPES.items():
                if ext in extensions:
                    return file_type

            # Try to detect by content if extension unknown
            if path_obj.exists():
                try:
                    with open(path_obj, 'rb') as f:
                        header = f.read(512)

                    # Check for common file signatures
                    if header.startswith(b'%PDF'):
                        return 'pdf'
                    elif header.startswith(b'PK\x03\x04'):  # ZIP signature (used by DOCX, XLSX)
                        return 'archive'
                    elif header.startswith(b'<?xml') or header.startswith(b'<'):
                        return 'xml'
                    elif header.startswith(b'{') or header.startswith(b'['):
                        return 'json'

                except Exception:
                    pass  # Fall back to unknown

            return 'unknown'

        except Exception as e:
            write_log(f"Error determining file type for {self.file_path}: {str(e)}", "warning")
            return 'unknown'

    def _get_file_info(self) -> Dict[str, Any]:
        """Get cached file information."""
        if self.file_info is None:
            try:
                self.file_info = get_file_info(self.file_path)
            except FileOperationError as e:
                write_log(f"Error getting file info: {str(e)}", "warning")
                self.file_info = {"exists": False}
        return self.file_info

    def check_file_exists(self) -> bool:
        """Check if file exists with proper error handling."""
        try:
            info = self._get_file_info()
            return info.get("exists", False)
        except Exception as e:
            write_log(f"Error checking file existence: {str(e)}", "error")
            return False

    def check_file_not_empty(self) -> bool:
        """Check if file is not empty with size validation."""
        try:
            if not self.check_file_exists():
                return False

            info = self._get_file_info()
            size = info.get("size", 0)

            # Consider file empty if size is 0
            return size > 0

        except Exception as e:
            write_log(f"Error checking file emptiness: {str(e)}", "error")
            return False

    def check_file_readable(self) -> bool:
        """Check if file is readable with multiple encoding attempts."""
        try:
            if not self.check_file_exists():
                return False

            path_obj = Path(self.file_path)

            # Try different encodings in order of preference
            encodings_to_try = [DEFAULT_ENCODING, 'latin-1', 'cp1252']

            for encoding in encodings_to_try:
                try:
                    with open(path_obj, 'r', encoding=encoding) as f:
                        f.read(1)  # Try to read one character
                    return True
                except UnicodeDecodeError:
                    continue  # Try next encoding
                except (PermissionError, OSError):
                    return False  # Permission or OS error

            # If all encodings failed, file is not readable with common encodings
            return False

        except Exception as e:
            write_log(f"Error checking file readability: {str(e)}", "warning")
            return False

    def _determine_status(self, file_exists: bool, file_not_empty: bool, file_readable: bool) -> Dict[str, Any]:
        """Determine validation status and human-readable summary."""
        status = {
            "file_exists": file_exists,
            "file_not_empty": file_not_empty,
            "file_readable": file_readable
        }

        if not file_exists:
            status.update({
                "status": "FILE_NOT_FOUND",
                "message": "File not found",
                "errors": f"File does not exist at path: {self.file_path}"
            })
            return status

        if not file_not_empty:
            status.update({
                "status": "EMPTY_FILE",
                "message": "File exists but is empty",
                "errors": "File size is zero bytes"
            })
            return status

        if not file_readable:
            status.update({
                "status": "UNREADABLE_FILE",
                "message": "File exists but cannot be read",
                "errors": "File may be corrupted, have permission issues, or unsupported encoding"
            })
            return status

        status.update({
            "status": "SUCCESS",
            "message": "Validation completed successfully",
            "errors": None
        })
        return status

    def _build_standardized_result(self, status_meta: Dict[str, Any], file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build the standardized validation result payload."""
        return {
            "document_id": self.document_id,
            "standardized_data": {
                "file_details": {
                    "file_path": self.file_path,
                    "file_type": self._get_file_type(),
                    "created_at": file_info.get("created", "N/A"),
                    "size_bytes": file_info.get("size", 0),
                    "last_modified": file_info.get("modified", "N/A")
                },
                "validation": {
                    "file_exists": status_meta["file_exists"],
                    "file_not_empty": status_meta["file_not_empty"],
                    "file_readable": status_meta["file_readable"],
                    "status": status_meta["status"]
                },
                "summary": {
                    "message": status_meta["message"],
                    "errors": status_meta["errors"],
                    "validation_timestamp": datetime.datetime.now().isoformat()
                },
                "metadata": {
                    "processed_by": self.system_name,
                    "version": self.version,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "validator_class": self.__class__.__name__
                }
            }
        }

    def validate(self) -> Dict[str, Any]:
        """
        Perform comprehensive validation and return standardized result.

        Returns:
            Dict containing validation results in standardized format
        """
        try:
            write_log(f"Starting validation for document: {self.document_id}")

            file_exists = self.check_file_exists()
            file_not_empty = self.check_file_not_empty()
            file_readable = self.check_file_readable()

            status_meta = self._determine_status(file_exists, file_not_empty, file_readable)
            file_info = self._get_file_info()
            result = self._build_standardized_result(status_meta, file_info)

            write_log(
                f"Validation completed for {self.file_path}: status={status_meta['status']}, document_id={self.document_id}"
            )
            return result

        except Exception as e:
            error_msg = f"Unexpected validation error: {str(e)}"
            write_log(error_msg, "error")
            return {
                "document_id": self.document_id,
                "standardized_data": {
                    "file_details": {
                        "file_path": self.file_path,
                        "file_type": "unknown",
                        "created_at": "N/A"
                    },
                    "validation": {
                        "file_exists": False,
                        "file_not_empty": False,
                        "file_readable": False,
                        "status": "VALIDATION_ERROR"
                    },
                    "summary": {
                        "message": "Validation failed due to unexpected error",
                        "errors": error_msg
                    },
                    "metadata": {
                        "processed_by": self.system_name,
                        "version": self.version,
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
            }

    def to_json(self, indent: int = 2) -> str:
        """
        Return validation result as formatted JSON string.

        Args:
            indent: JSON indentation level

        Returns:
            str: JSON representation of validation result
        """
        try:
            return json.dumps(self.validate(), indent=indent, ensure_ascii=False)
        except Exception as e:
            write_log(f"Error converting validation result to JSON: {str(e)}", "error")
            return json.dumps({"error": "Failed to serialize validation result"})

    def save_result(self, output_path: Union[str, Path]) -> None:
        """
        Save validation result to JSON file.

        Args:
            output_path: Path to save the result
        """
        try:
            from src.utils import write_json
            result = self.validate()
            write_json(output_path, result)
            write_log(f"Validation result saved to: {output_path}")
        except Exception as e:
            write_log(f"Error saving validation result: {str(e)}", "error")
            raise


class StandardizedDataValidator:
    """
    Validates standardized payloads against schema and business rules.

    This validator is designed for payloads of the form:
        {"document_id": "DOC001", "standardized_data": {...}}
    """

    STATUS_RULES = {
        "SUCCESS": {
            "file_exists": True,
            "file_not_empty": True,
            "file_readable": True,
            "errors": None
        },
        "FILE_NOT_FOUND": {
            "file_exists": False,
            "file_not_empty": False
        },
        "EMPTY_FILE": {
            "file_exists": True,
            "file_not_empty": False
        },
        "UNREADABLE_FILE": {
            "file_exists": True,
            "file_not_empty": True,
            "file_readable": False
        },
        "VALIDATION_ERROR": {
            "file_exists": False,
            "file_not_empty": False
        }
    }

    def __init__(self, payload: Union[Dict[str, Any], str]):
        self.payload = self._parse_payload(payload)
        self.errors: List[str] = []
        self.rule_violations: List[str] = []
        write_log("Initialized standardized payload validator")

    def _parse_payload(self, payload: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON payload: {str(e)}")

        if not isinstance(payload, dict):
            raise ValidationError("Payload must be a JSON object")

        return payload

    def _check_required_keys(self, obj: Dict[str, Any], keys: List[str], path: str) -> None:
        for key in keys:
            if key not in obj:
                self.errors.append(f"Missing required key '{key}' in {path}")

    def _check_type(self, value: Any, expected_type: type, path: str) -> None:
        if not isinstance(value, expected_type):
            self.errors.append(f"Expected {path} to be {expected_type.__name__}, got {type(value).__name__}")

    def _parse_datetime(self, value: Any, path: str) -> None:
        if not isinstance(value, str):
            self.errors.append(f"Expected {path} to be ISO datetime string")
            return
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]:
            try:
                datetime.datetime.strptime(value, fmt)
                return
            except ValueError:
                continue
        self.errors.append(f"{path} is not in a supported datetime format")

    def _validate_schema(self) -> None:
        payload = self.payload

        self._check_required_keys(payload, ["document_id", "standardized_data"], "root")
        if self.errors:
            return

        self._check_type(payload["document_id"], str, "document_id")
        self._check_type(payload["standardized_data"], dict, "standardized_data")

        standardized = payload["standardized_data"]
        self._check_required_keys(standardized, ["file_details", "validation", "summary", "metadata"], "standardized_data")
        if self.errors:
            return

        self._check_type(standardized["file_details"], dict, "file_details")
        self._check_type(standardized["validation"], dict, "validation")
        self._check_type(standardized["summary"], dict, "summary")
        self._check_type(standardized["metadata"], dict, "metadata")

        file_details = standardized["file_details"]
        validation = standardized["validation"]
        summary = standardized["summary"]
        metadata = standardized["metadata"]

        self._check_required_keys(file_details, ["file_path", "file_type", "created_at"], "file_details")
        self._check_required_keys(validation, ["file_exists", "file_not_empty", "file_readable", "status"], "validation")
        self._check_required_keys(summary, ["message", "errors"], "summary")
        self._check_required_keys(metadata, METADATA_KEYS, "metadata")

        if self.errors:
            return

        self._check_type(file_details["file_path"], str, "file_details.file_path")
        self._check_type(file_details["file_type"], str, "file_details.file_type")
        self._parse_datetime(file_details["created_at"], "file_details.created_at")

        self._check_type(validation["file_exists"], bool, "validation.file_exists")
        self._check_type(validation["file_not_empty"], bool, "validation.file_not_empty")
        self._check_type(validation["file_readable"], bool, "validation.file_readable")
        self._check_type(validation["status"], str, "validation.status")

        self._check_type(summary["message"], str, "summary.message")
        if summary["errors"] is not None and not isinstance(summary["errors"], str):
            self.errors.append("summary.errors must be None or a string")

        self._check_type(metadata["processed_by"], str, "metadata.processed_by")
        self._check_type(metadata["version"], str, "metadata.version")
        self._parse_datetime(metadata["timestamp"], "metadata.timestamp")

    def _evaluate_business_rules(self) -> None:
        agent = BusinessRulesAgent(self.payload)
        outcome = agent.validate()

        if outcome.get("business_rule_violations"):
            self.rule_violations.extend(outcome["business_rule_violations"])

        if outcome.get("business_warnings"):
            self.business_warnings = outcome["business_warnings"]
        else:
            self.business_warnings = []

    def validate(self) -> Dict[str, Any]:
        self.errors = []
        self.rule_violations = []
        self.business_warnings: List[str] = []

        try:
            self._validate_schema()
            if not self.errors:
                self._evaluate_business_rules()

            passed = not self.errors and not self.rule_violations
            result = {
                "document_id": self.payload.get("document_id", "UNKNOWN"),
                "validation_passed": passed,
                "schema_errors": self.errors,
                "business_rule_violations": self.rule_violations,
                "business_warnings": self.business_warnings,
                "source": "standardized_payload"
            }
            write_log(f"Payload validation completed: passed={passed}, document_id={result['document_id']}")
            return result
        except ValidationError as e:
            write_log(f"Payload validation failed: {str(e)}", "error")
            return {
                "document_id": self.payload.get("document_id", "UNKNOWN") if isinstance(self.payload, dict) else "UNKNOWN",
                "validation_passed": False,
                "schema_errors": [str(e)],
                "business_rule_violations": [],
                "business_warnings": [],
                "source": "standardized_payload"
            }

    def to_json(self, indent: int = 2) -> str:
        try:
            return json.dumps(self.validate(), indent=indent, ensure_ascii=False)
        except Exception as e:
            write_log(f"Error serializing payload validation result: {str(e)}", "error")
            return json.dumps({"error": "Failed to serialize payload validation result"})


# Direct run support (for testing)
if __name__ == "__main__":
    import sys

    file_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/sample.txt"
    document_id = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        validator = DataValidator(file_path, document_id)
        output = validator.validate()
        print(validator.to_json())
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)