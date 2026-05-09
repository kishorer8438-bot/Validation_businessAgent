"""
RAG Validation System - Professional File Validation Framework

This package provides comprehensive file validation capabilities
for RAG (Retrieval-Augmented Generation) systems with standardized
output formats and robust error handling.

Modules:
- validator: Core validation logic and DataValidator class
- utils: Utility functions for file operations and logging
- main: CLI interface and pipeline orchestration

Author: RAG Validation System Team
Version: 1.0
"""

__version__ = "1.0"
__author__ = "RAG Validation System Team"
__description__ = "Professional file validation system for RAG applications"

# Import main classes for easy access
from .validator import DataValidator
from .business_agent import BusinessRulesAgent
from .utils import (
    write_log, read_file, write_file, write_json, read_json,
    create_directory, get_file_info, ValidationError, FileOperationError
)

__all__ = [
    "DataValidator",
    "write_log",
    "read_file",
    "write_file",
    "write_json",
    "read_json",
    "create_directory",
    "get_file_info",
    "ValidationError",
    "FileOperationError",
    "__version__",
    "__author__",
    "__description__"
]