"""
Business agent for the RAG Validation System.
Handles business-rule evaluation for standardized payloads and validation results.
"""

import datetime
import json
from typing import Any, Dict, List, Union

from .utils import ValidationError, write_log


class BusinessRulesAgent:
    """Encapsulates business logic for standardized validation payloads."""

    REQUIRED_ROOT_KEYS = ["document_id", "standardized_data"]
    REQUIRED_STANDARDIZED_KEYS = ["file_details", "validation", "summary", "metadata"]
    REQUIRED_FILE_DETAILS = ["file_path", "file_type", "created_at"]
    REQUIRED_VALIDATION_FIELDS = ["file_exists", "file_not_empty", "file_readable", "status"]
    REQUIRED_SUMMARY_FIELDS = ["message", "errors"]
    REQUIRED_METADATA_FIELDS = ["processed_by", "version", "timestamp"]

    STATUS_EXPECTATIONS = {
        "SUCCESS": {
            "file_exists": True,
            "file_not_empty": True,
            "file_readable": True
        },
        "FILE_NOT_FOUND": {
            "file_exists": False,
            "file_not_empty": False,
            "file_readable": False
        },
        "EMPTY_FILE": {
            "file_exists": True,
            "file_not_empty": False,
            "file_readable": True
        },
        "UNREADABLE_FILE": {
            "file_exists": True,
            "file_not_empty": True,
            "file_readable": False
        },
        "VALIDATION_ERROR": {
            "file_exists": False,
            "file_not_empty": False,
            "file_readable": False
        }
    }

    def __init__(self, payload: Union[Dict[str, Any], str]):
        self.payload = self._parse_payload(payload)
        self.violations: List[str] = []
        self.warnings: List[str] = []
        write_log("BusinessRulesAgent initialized")

    def _parse_payload(self, payload: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON payload: {str(e)}")

        if not isinstance(payload, dict):
            raise ValidationError("Payload must be a JSON object")

        return payload

    def _ensure_required_keys(self, obj: Dict[str, Any], keys: List[str], path: str) -> None:
        for key in keys:
            if key not in obj:
                self.violations.append(f"Missing required key '{key}' in {path}")

    def _log_violation(self, message: str) -> None:
        """Helper method to log and append violations."""
        self.violations.append(message)
        write_log(message, "warning")

    def _log_warning(self, message: str) -> None:
        """Helper method to log and append warnings."""
        self.warnings.append(message)
        write_log(message, "info")

    def _parse_datetime(self, value: Any, path: str) -> None:
        if not isinstance(value, str):
            self._log_violation(f"Expected {path} to be ISO datetime string")
            return
        formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]
        for fmt in formats:
            try:
                datetime.datetime.strptime(value, fmt)
                return
            except ValueError:
                continue
        self._log_violation(f"{path} is not in a supported datetime format")

    def _validate_required_structure(self) -> None:
        self._ensure_required_keys(self.payload, self.REQUIRED_ROOT_KEYS, "root")
        if self.violations:
            return

        standardized = self.payload.get("standardized_data")
        if not isinstance(standardized, dict):
            self._log_violation("standardized_data must be an object")
            return

        self._ensure_required_keys(standardized, self.REQUIRED_STANDARDIZED_KEYS, "standardized_data")
        if self.violations:
            return

        file_details = standardized["file_details"]
        validation = standardized["validation"]
        summary = standardized["summary"]
        metadata = standardized["metadata"]

        if not isinstance(file_details, dict):
            self._log_violation("file_details must be an object")
        else:
            self._ensure_required_keys(file_details, self.REQUIRED_FILE_DETAILS, "file_details")
            if "created_at" in file_details:
                self._parse_datetime(file_details["created_at"], "file_details.created_at")

        if not isinstance(validation, dict):
            self._log_violation("validation must be an object")
        else:
            self._ensure_required_keys(validation, self.REQUIRED_VALIDATION_FIELDS, "validation")
            self._check_validation_types(validation)

        if not isinstance(summary, dict):
            self._log_violation("summary must be an object")
        else:
            self._ensure_required_keys(summary, self.REQUIRED_SUMMARY_FIELDS, "summary")
            if "message" in summary and not isinstance(summary["message"], str):
                self._log_violation("summary.message must be a string")
            if "errors" in summary and summary["errors"] is not None and not isinstance(summary["errors"], str):
                self._log_violation("summary.errors must be None or a string")

        if not isinstance(metadata, dict):
            self._log_violation("metadata must be an object")
        else:
            self._ensure_required_keys(metadata, self.REQUIRED_METADATA_FIELDS, "metadata")
            if "timestamp" in metadata:
                self._parse_datetime(metadata["timestamp"], "metadata.timestamp")
            if "processed_by" in metadata and not isinstance(metadata["processed_by"], str):
                self._log_violation("metadata.processed_by must be a string")
            if "version" in metadata and not isinstance(metadata["version"], str):
                self._log_violation("metadata.version must be a string")

    def _check_validation_types(self, validation: Dict[str, Any]) -> None:
        if "file_exists" in validation and not isinstance(validation["file_exists"], bool):
            self._log_violation("validation.file_exists must be a boolean")
        if "file_not_empty" in validation and not isinstance(validation["file_not_empty"], bool):
            self._log_violation("validation.file_not_empty must be a boolean")
        if "file_readable" in validation and not isinstance(validation["file_readable"], bool):
            self._log_violation("validation.file_readable must be a boolean")
        if "status" in validation and not isinstance(validation["status"], str):
            self._log_violation("validation.status must be a string")

    def _extract_validation(self) -> Dict[str, Any]:
        try:
            return self.payload["standardized_data"]["validation"]
        except KeyError:
            raise ValidationError("standardized_data.validation section is missing")

    def _extract_summary(self) -> Dict[str, Any]:
        try:
            return self.payload["standardized_data"]["summary"]
        except KeyError:
            raise ValidationError("standardized_data.summary section is missing")

    def _validate_status_rules(self) -> None:
        validation = self._extract_validation()
        summary = self._extract_summary()

        status = validation.get("status")
        if status not in self.STATUS_EXPECTATIONS:
            self._log_violation(f"Unsupported status '{status}'")
            return

        expected = self.STATUS_EXPECTATIONS[status]
        for key, expected_value in expected.items():
            actual_value = validation.get(key)
            if actual_value != expected_value:
                self._log_violation(
                    f"Status '{status}' requires {key}={expected_value}, found {actual_value}"
                )

        if status == "SUCCESS" and summary.get("errors") is not None:
            self._log_violation("SUCCESS status must have summary.errors set to null")
        if status != "SUCCESS" and summary.get("errors") is None:
            self._log_violation(f"Status '{status}' must include a non-null summary.errors message")

    def _validate_consistency_rules(self) -> None:
        validation = self._extract_validation()
        status = validation.get("status")

        if validation.get("file_exists") is False and validation.get("file_not_empty") is True:
            self._log_violation("file_not_empty cannot be true when file_exists is false")

        if status == "UNREADABLE_FILE" and validation.get("file_readable"):
            self._log_violation("UNREADABLE_FILE requires file_readable to be false")

        if status == "FILE_NOT_FOUND" and validation.get("file_readable"):
            self._log_violation("FILE_NOT_FOUND requires file_readable to be false")

    def _validate_metadata_rules(self) -> None:
        metadata = self.payload.get("standardized_data", {}).get("metadata", {})

        if metadata.get("processed_by") is None:
            self._log_warning("metadata.processed_by is missing")
        if metadata.get("version") is None:
            self._log_warning("metadata.version is missing")
        if metadata.get("timestamp") is None:
            self._log_warning("metadata.timestamp is missing")

    def validate(self) -> Dict[str, Any]:
        self.violations = []
        self.warnings = []

        try:
            self._validate_required_structure()
            if not self.violations:
                self._validate_status_rules()
                self._validate_consistency_rules()
                self._validate_metadata_rules()

            result = {
                "validation_passed": len(self.violations) == 0,
                "business_rule_violations": self.violations,
                "business_warnings": self.warnings,
                "evaluated_at": datetime.datetime.now().isoformat(),
                "source": "business_agent"
            }

            write_log(f"Business rules evaluation completed: passed={result['validation_passed']}")
            return result
        except ValidationError as e:
            write_log(f"Business rules validation failed: {str(e)}", "error")
            return {
                "validation_passed": False,
                "business_rule_violations": [str(e)],
                "business_warnings": [],
                "evaluated_at": datetime.datetime.now().isoformat(),
                "source": "business_agent"
            }
