"""
Main entry point for RAG Validation System
Provides CLI interface for file validation with comprehensive options.
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

from .validator import DataValidator, StandardizedDataValidator
from .utils import (
    create_directory, write_log, write_json, read_json,
    list_files, ValidationError, FileOperationError
)

# Expose a FastAPI app object so `uvicorn src.main:app` works.
from fastapi import FastAPI
try:
    from .api import app as api_app
except Exception:
    api_app = None

# Main ASGI app (keeps separate from src.api.app but will reuse its routes)
app = FastAPI(title="RAG Validation API (main)", version="1.0")


@app.get("/", summary="Service health")
def root() -> dict:
    return {"message": "RAG Validation API is running."}


@app.get("/health", summary="Health check")
def health() -> dict:
    return {"message": "RAG Validation API is running."}

# If the API app from src.api is available, copy its routes into this app
# (skip root/health to avoid duplicate paths).
if api_app is not None:
    for route in api_app.router.routes:
        path = getattr(route, "path", None)
        if path in ("/", "/health"):
            continue
        app.router.routes.append(route)


class ValidationConfig:
    """Configuration class for validation settings."""

    def __init__(self, config_file: Optional[str] = None):
        self.default_output_dir = "outputs"
        self.default_log_file = "logs/validation.log"
        self.batch_mode = False
        self.verbose = False
        self.save_results = True
        self.system_name = "RAG Validation System"
        self.version = "1.0"

        if config_file and Path(config_file).exists():
            self.load_config(config_file)

    def load_config(self, config_file: str) -> None:
        """Load configuration from JSON file."""
        try:
            config_data = read_json(config_file)
            for key, value in config_data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            write_log(f"Loaded configuration from {config_file}")
        except Exception as e:
            write_log(f"Error loading config {config_file}: {str(e)}", "warning")


def setup_cli_parser() -> argparse.ArgumentParser:
    """Setup comprehensive command line argument parser."""
    parser = argparse.ArgumentParser(
        description="RAG Data Validation System - Professional File Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main data/raw/sample.txt
  python -m src.main data/raw/ --batch --output results/
  python -m src.main file.txt --document-id DOC001 --config config.json
  python -m src.main data/raw/*.txt --batch --verbose
        """
    )

    # File/Directory arguments
    parser.add_argument(
        "file_path",
        help="Path to file or directory to validate"
    )

    # Optional arguments
    parser.add_argument(
        "--document-id",
        help="Custom document ID (auto-generated if not provided)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file/directory path",
        default="outputs/result.json"
    )
    parser.add_argument(
        "--config", "-c",
        help="Configuration file path"
    )
    parser.add_argument(
        "--batch", "-b",
        action="store_true",
        help="Process directory in batch mode"
    )
    parser.add_argument(
        "--payload",
        action="store_true",
        help="Treat input file as standardized JSON payload for business rule validation"
    )
    parser.add_argument(
        "--payload-file",
        action="store_true",
        help="Alias for --payload; validate a standardized JSON payload file"
    )
    parser.add_argument(
        "--pattern", "-p",
        help="File pattern for batch processing (default: *)",
        default="*"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--system-name",
        help="Override system name",
        default="RAG Validation System"
    )

    return parser


def validate_single_file(file_path: str, config: ValidationConfig,
                        document_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate a single file and return results.

    Args:
        file_path: Path to file to validate
        config: Validation configuration
        document_id: Optional document ID

    Returns:
        Dict containing validation results
    """
    try:
        if config.verbose:
            print(f"🔍 Validating: {file_path}")

        validator = DataValidator(
            file_path,
            document_id,
            config.system_name,
            config.version
        )

        result = validator.validate()

        if config.verbose:
            status = result["standardized_data"]["validation"]["status"]
            print(f"✅ {file_path}: {status}")

        return result

    except Exception as e:
        error_result = {
            "document_id": document_id or "ERROR",
            "error": str(e),
            "file_path": file_path,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        write_log(f"Validation failed for {file_path}: {str(e)}", "error")
        return error_result


def validate_payload_file(payload_path: str) -> Dict[str, Any]:
    """Validate either a standardized payload file or the enterprise input schema.

    If `payload_path` contains `standardized_data`, run `StandardizedDataValidator`.
    Otherwise, if it contains `file_details`, run `DataValidator` on the nested file path.
    """
    payload = None
    try:
        payload = read_json(payload_path)

        # Standardized payload (legacy)
        if isinstance(payload, dict) and payload.get("standardized_data"):
            validator = StandardizedDataValidator(payload)
            return validator.validate()

        # Enterprise input schema with nested file_details
        if isinstance(payload, dict) and payload.get("file_details") and payload["file_details"].get("file_path"):
            file_path = payload["file_details"]["file_path"]
            document_id = payload.get("document_id")
            validator = DataValidator(file_path, document_id)
            return validator.validate()

        raise ValueError("Payload does not contain a recognized payload shape")
    except Exception as e:
        write_log(f"Payload validation failed for {payload_path}: {str(e)}", "error")
        doc_id = payload.get("document_id") if isinstance(payload, dict) else "UNKNOWN"
        return {
            "document_id": doc_id,
            "validation_passed": False,
            "schema_errors": [f"Invalid JSON in file {payload_path}: {str(e)}"],
            "business_rule_violations": [],
            "source": "standardized_payload"
        }


def validate_batch(files: List[Path], config: ValidationConfig) -> List[Dict[str, Any]]:
    """
    Validate multiple files in batch mode.

    Args:
        files: List of file paths to validate
        config: Validation configuration

    Returns:
        List of validation results
    """
    results = []
    total_files = len(files)

    print(f"🚀 Starting batch validation of {total_files} files...\n")

    for i, file_path in enumerate(files, 1):
        if config.verbose:
            print(f"[{i}/{total_files}] ", end="")

        result = validate_single_file(str(file_path), config)
        results.append(result)

        # Progress indicator for non-verbose mode
        if not config.verbose and i % 10 == 0:
            print(f"Processed {i}/{total_files} files...")

    print(f"\n✅ Batch validation completed: {total_files} files processed")
    return results


def save_results(results: List[Dict[str, Any]], output_path: str,
                config: ValidationConfig) -> None:
    """
    Save validation results to file(s).

    Args:
        results: List of validation results
        output_path: Output path
        config: Validation configuration
    """
    try:
        output_path_obj = Path(output_path)

        if len(results) == 1:
            if output_path_obj.is_dir() or not output_path_obj.suffix:
                output_path_obj.mkdir(parents=True, exist_ok=True)
                output_path_obj = output_path_obj / f"{results[0].get('document_id', 'result')}.json"
            else:
                create_directory(output_path_obj.parent)
            write_json(output_path_obj, results[0])
            print(f"💾 Result saved to: {output_path_obj}")
            return

        if output_path_obj.is_dir() or not output_path_obj.suffix:
            output_path_obj.mkdir(parents=True, exist_ok=True)
            for result in results:
                doc_id = result.get("document_id", "unknown")
                file_name = f"{doc_id}.json"
                file_path = output_path_obj / file_name
                write_json(file_path, result)
            print(f"💾 Batch results saved to: {output_path_obj}/")
        else:
            create_directory(output_path_obj.parent)
            write_json(output_path_obj, results)
            print(f"💾 Batch results saved to: {output_path}")

    except Exception as e:
        write_log(f"Error saving results: {str(e)}", "error")
        print(f"❌ Error saving results: {str(e)}")


def main() -> int:
    parser = setup_cli_parser()
    args = parser.parse_args()

    config = ValidationConfig(args.config)
    config.batch_mode = args.batch
    config.verbose = args.verbose
    config.save_results = not args.no_save
    config.system_name = args.system_name

    if args.batch:
        target_path = Path(args.file_path)
        if not target_path.exists() or not target_path.is_dir():
            print(f"❌ Batch mode requires an existing directory path: {args.file_path}")
            return 1

        files = [f for f in list_files(target_path, args.pattern) if f.is_file()]
        if not files:
            print(f"⚠️ No files found in {args.file_path} matching pattern '{args.pattern}'")
            return 1

        results = validate_batch(files, config)
        if config.save_results:
            save_results(results, args.output, config)
        return 0

    if args.payload or args.payload_file:
        result = validate_payload_file(args.file_path)
        if config.save_results and isinstance(result, dict):
            output_path = args.output or f"outputs/{result.get('document_id', 'UNKNOWN')}.json"
            save_results([result], output_path, config)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    result = validate_single_file(args.file_path, config, args.document_id)
    if config.save_results and isinstance(result, dict):
        save_results([result], args.output, config)

    if args.format == "text":
        validation = result.get("standardized_data", {}).get("validation", {})
        print(f"Status: {validation.get('status', 'UNKNOWN')}\nMessage: {result.get('standardized_data', {}).get('summary', {}).get('message', '')}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


