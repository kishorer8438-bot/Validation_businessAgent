"""
Utility functions for RAG Validation System
Provides robust file operations, logging, and data handling utilities.
"""

import os
import json
import logging
import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import shutil


# Configuration Constants
DEFAULT_LOG_FILE = "logs/app.log"
DEFAULT_ENCODING = "utf-8"
MAX_FILE_SIZE_MB = 100  # Maximum file size to process
BACKUP_SUFFIX = ".backup"


class ValidationError(Exception):
    """Custom exception for validation operations."""
    pass


class FileOperationError(Exception):
    """Custom exception for file operations."""
    pass


def setup_logging(log_file: str = DEFAULT_LOG_FILE, level: int = logging.INFO) -> None:
    """Setup comprehensive logging configuration."""
    create_directory(os.path.dirname(log_file))

    logging.basicConfig(
        filename=log_file,
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Also log to console
    console = logging.StreamHandler()
    console.setLevel(level)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


def create_directory(path: Union[str, Path]) -> bool:
    """
    Create directory if it doesn't exist.

    Args:
        path: Directory path to create

    Returns:
        bool: True if directory was created or already exists

    Raises:
        FileOperationError: If directory creation fails
    """
    try:
        if not path:
            return False

        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        raise FileOperationError(f"Failed to create directory {path}: {str(e)}")


def get_current_timestamp(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Get current timestamp in specified format.

    Args:
        format_str: Timestamp format string

    Returns:
        str: Formatted timestamp
    """
    return datetime.datetime.now().strftime(format_str)


def write_log(message: str, level: str = "info", log_file: str = DEFAULT_LOG_FILE) -> None:
    """
    Write log message with proper formatting and error handling.

    Args:
        message: Log message
        level: Log level (debug, info, warning, error, critical)
        log_file: Log file path
    """
    try:
        create_directory(os.path.dirname(log_file))

        timestamp = get_current_timestamp()
        level_upper = level.upper()

        with open(log_file, "a", encoding=DEFAULT_ENCODING) as f:
            f.write(f"[{timestamp}] {level_upper}: {message}\n")

        # Also use Python logging if configured
        logger = logging.getLogger(__name__)
        log_method = getattr(logger, level.lower(), logger.info)
        log_method(message)

    except Exception as e:
        # Fallback to print if logging fails
        print(f"LOG ERROR: {message} - Logging failed: {str(e)}")


def validate_file_path(file_path: Union[str, Path]) -> Path:
    """
    Validate and normalize file path.

    Args:
        file_path: File path to validate

    Returns:
        Path: Normalized Path object

    Raises:
        ValidationError: If path is invalid
    """
    if not file_path:
        raise ValidationError("File path cannot be empty")

    path_obj = Path(file_path).resolve()

    # Check for dangerous paths
    if ".." in str(path_obj) and not path_obj.is_absolute():
        raise ValidationError("Relative paths with '..' are not allowed")

    return path_obj


def read_file(file_path: Union[str, Path], encoding: str = DEFAULT_ENCODING) -> str:
    """
    Read file content with proper error handling and size limits.

    Args:
        file_path: Path to file
        encoding: File encoding

    Returns:
        str: File content

    Raises:
        FileOperationError: If reading fails
        ValidationError: If file is too large
    """
    try:
        path_obj = validate_file_path(file_path)

        if not path_obj.exists():
            return ""

        # Check file size
        file_size = path_obj.stat().st_size
        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise ValidationError(f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE_MB}MB)")

        with open(path_obj, "r", encoding=encoding) as f:
            content = f.read()

        write_log(f"Successfully read file: {file_path}")
        return content

    except UnicodeDecodeError as e:
        raise FileOperationError(f"Encoding error reading {file_path}: {str(e)}")
    except Exception as e:
        raise FileOperationError(f"Failed to read file {file_path}: {str(e)}")


def write_file(file_path: Union[str, Path], content: str, encoding: str = DEFAULT_ENCODING,
               create_backup: bool = False) -> None:
    """
    Write content to file with backup and error handling.

    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding
        create_backup: Whether to create backup of existing file

    Raises:
        FileOperationError: If writing fails
    """
    try:
        path_obj = validate_file_path(file_path)

        # Create backup if requested and file exists
        if create_backup and path_obj.exists():
            backup_path = path_obj.with_suffix(path_obj.suffix + BACKUP_SUFFIX)
            shutil.copy2(path_obj, backup_path)
            write_log(f"Created backup: {backup_path}")

        create_directory(path_obj.parent)

        with open(path_obj, "w", encoding=encoding) as f:
            f.write(content)

        write_log(f"Successfully wrote file: {file_path}")

    except Exception as e:
        raise FileOperationError(f"Failed to write file {file_path}: {str(e)}")


def write_json(file_path: Union[str, Path], data: Any, indent: int = 2,
               ensure_ascii: bool = False, create_backup: bool = False) -> None:
    """
    Write JSON data to file with proper formatting.

    Args:
        file_path: Path to JSON file
        data: Data to serialize
        indent: JSON indentation
        ensure_ascii: Whether to escape non-ASCII characters
        create_backup: Whether to create backup

    Raises:
        FileOperationError: If writing fails
    """
    try:
        path_obj = validate_file_path(file_path)
        create_directory(path_obj.parent)

        # Create backup if requested
        if create_backup and path_obj.exists():
            backup_path = path_obj.with_suffix(path_obj.suffix + BACKUP_SUFFIX)
            shutil.copy2(path_obj, backup_path)

        with open(path_obj, "w", encoding=DEFAULT_ENCODING) as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)

        write_log(f"Successfully wrote JSON file: {file_path}")

    except Exception as e:
        raise FileOperationError(f"Failed to write JSON file {file_path}: {str(e)}")


def read_json(file_path: Union[str, Path]) -> Any:
    """
    Read JSON data from file.

    Args:
        file_path: Path to JSON file

    Returns:
        Any: Parsed JSON data

    Raises:
        FileOperationError: If reading or parsing fails
    """
    try:
        path_obj = validate_file_path(file_path)

        if not path_obj.exists():
            raise FileOperationError(f"JSON file does not exist: {file_path}")

        with open(path_obj, "r", encoding=DEFAULT_ENCODING) as f:
            data = json.load(f)

        write_log(f"Successfully read JSON file: {file_path}")
        return data

    except json.JSONDecodeError as e:
        raise FileOperationError(f"Invalid JSON in file {file_path}: {str(e)}")
    except Exception as e:
        raise FileOperationError(f"Failed to read JSON file {file_path}: {str(e)}")


def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get comprehensive file information.

    Args:
        file_path: Path to file

    Returns:
        Dict containing file metadata

    Raises:
        FileOperationError: If file access fails
    """
    try:
        path_obj = validate_file_path(file_path)

        if not path_obj.exists():
            return {
                "exists": False,
                "path": str(path_obj),
                "size": 0,
                "created": None,
                "modified": None
            }

        stat = path_obj.stat()

        return {
            "exists": True,
            "path": str(path_obj),
            "size": stat.st_size,
            "created": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_file": path_obj.is_file(),
            "is_dir": path_obj.is_dir()
        }

    except Exception as e:
        raise FileOperationError(f"Failed to get file info for {file_path}: {str(e)}")


def safe_delete(file_path: Union[str, Path]) -> bool:
    """
    Safely delete a file with error handling.

    Args:
        file_path: Path to file to delete

    Returns:
        bool: True if deleted successfully

    Raises:
        FileOperationError: If deletion fails
    """
    try:
        path_obj = validate_file_path(file_path)

        if not path_obj.exists():
            return True

        path_obj.unlink()
        write_log(f"Successfully deleted file: {file_path}")
        return True

    except Exception as e:
        raise FileOperationError(f"Failed to delete file {file_path}: {str(e)}")


def list_files(directory: Union[str, Path], pattern: str = "*") -> List[Path]:
    """
    List files in directory matching pattern.

    Args:
        directory: Directory path
        pattern: Glob pattern to match

    Returns:
        List of matching file paths

    Raises:
        FileOperationError: If directory access fails
    """
    try:
        path_obj = validate_file_path(directory)

        if not path_obj.is_dir():
            raise ValidationError(f"Path is not a directory: {directory}")

        files = list(path_obj.glob(pattern))
        write_log(f"Listed {len(files)} files in {directory} matching {pattern}")
        return files

    except Exception as e:
        raise FileOperationError(f"Failed to list files in {directory}: {str(e)}")


# Initialize logging on import
setup_logging()


def append_file(file_path: str, content: str):
    """Append content to file"""
    create_directory(os.path.dirname(file_path))

    with open(file_path, "a") as f:
        f.write(content + "\n")