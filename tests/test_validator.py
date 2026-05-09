"""
Comprehensive test suite for RAG Validation System
Tests all aspects of the DataValidator class with various scenarios.
"""

import os
import json
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open

from src.validator import DataValidator, StandardizedDataValidator
from src.utils import ValidationError, FileOperationError


class TestDataValidator(unittest.TestCase):
    """Test cases for DataValidator class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.sample_content = "This is a test file content for validation."
        self.empty_content = ""

        # Create test files
        self.valid_file = self.test_dir / "valid.txt"
        self.empty_file = self.test_dir / "empty.txt"
        self.missing_file = self.test_dir / "missing.txt"

        # Setup test files
        self.valid_file.write_text(self.sample_content)
        self.empty_file.write_text(self.empty_content)

    def tearDown(self):
        """Clean up test fixtures after each test method."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_initialization_valid_file(self):
        """Test validator initialization with valid file."""
        validator = DataValidator(str(self.valid_file))
        self.assertIsNotNone(validator.document_id)
        self.assertTrue(validator.document_id.startswith("DOC"))
        self.assertEqual(validator.file_path, str(self.valid_file))

    def test_initialization_custom_document_id(self):
        """Test validator initialization with custom document ID."""
        custom_id = "TEST001"
        validator = DataValidator(str(self.valid_file), custom_id)
        self.assertEqual(validator.document_id, custom_id)

    def test_initialization_invalid_path(self):
        """Test validator initialization with invalid path."""
        with self.assertRaises(ValidationError):
            DataValidator("")

    def test_file_exists_check(self):
        """Test file existence checking."""
        validator = DataValidator(str(self.valid_file))
        self.assertTrue(validator.check_file_exists())

        validator_missing = DataValidator(str(self.missing_file))
        self.assertFalse(validator_missing.check_file_exists())

    def test_file_not_empty_check(self):
        """Test file emptiness checking."""
        validator = DataValidator(str(self.valid_file))
        self.assertTrue(validator.check_file_not_empty())

        validator_empty = DataValidator(str(self.empty_file))
        self.assertFalse(validator_empty.check_file_not_empty())

        validator_missing = DataValidator(str(self.missing_file))
        self.assertFalse(validator_missing.check_file_not_empty())

    def test_file_readable_check(self):
        """Test file readability checking."""
        validator = DataValidator(str(self.valid_file))
        self.assertTrue(validator.check_file_readable())

        validator_missing = DataValidator(str(self.missing_file))
        self.assertFalse(validator_missing.check_file_readable())

    def test_file_type_detection(self):
        """Test file type detection from extension."""
        test_cases = [
            ("test.txt", "text"),
            ("test.pdf", "pdf"),
            ("test.docx", "word"),
            ("test.xlsx", "excel"),
            ("test.json", "json"),
            ("test.xml", "xml"),
            ("test.unknown", "unknown"),
            ("test.py", "code"),
            ("test.yml", "config")
        ]

        for filename, expected_type in test_cases:
            with self.subTest(filename=filename):
                test_file = self.test_dir / filename
                test_file.write_text("content")
                validator = DataValidator(str(test_file))
                self.assertEqual(validator._get_file_type(), expected_type)

    def test_validation_success(self):
        """Test successful validation of valid file."""
        validator = DataValidator(str(self.valid_file), "DOC001")
        result = validator.validate()

        self.assertEqual(result["document_id"], "DOC001")
        self.assertEqual(result["standardized_data"]["validation"]["status"], "SUCCESS")
        self.assertTrue(result["standardized_data"]["validation"]["file_exists"])
        self.assertTrue(result["standardized_data"]["validation"]["file_not_empty"])
        self.assertTrue(result["standardized_data"]["validation"]["file_readable"])
        self.assertIsNone(result["standardized_data"]["summary"]["errors"])
        self.assertIn("Validation completed successfully", result["standardized_data"]["summary"]["message"])

    def test_validation_empty_file(self):
        """Test validation of empty file."""
        validator = DataValidator(str(self.empty_file))
        result = validator.validate()

        self.assertEqual(result["standardized_data"]["validation"]["status"], "EMPTY_FILE")
        self.assertTrue(result["standardized_data"]["validation"]["file_exists"])
        self.assertFalse(result["standardized_data"]["validation"]["file_not_empty"])
        self.assertIsNotNone(result["standardized_data"]["summary"]["errors"])

    def test_validation_missing_file(self):
        """Test validation of missing file."""
        validator = DataValidator(str(self.missing_file))
        result = validator.validate()

        self.assertEqual(result["standardized_data"]["validation"]["status"], "FILE_NOT_FOUND")
        self.assertFalse(result["standardized_data"]["validation"]["file_exists"])
        self.assertFalse(result["standardized_data"]["validation"]["file_not_empty"])
        self.assertIsNotNone(result["standardized_data"]["summary"]["errors"])

    def test_validation_unreadable_file(self):
        """Test validation of unreadable file."""
        # Create a file and remove read permissions (if possible)
        unreadable_file = self.test_dir / "unreadable.txt"
        unreadable_file.write_text("content")

        # Mock permission error
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            validator = DataValidator(str(unreadable_file))
            result = validator.validate()

            self.assertEqual(result["standardized_data"]["validation"]["status"], "UNREADABLE_FILE")
            self.assertFalse(result["standardized_data"]["validation"]["file_readable"])

    def test_to_json_method(self):
        """Test JSON serialization method."""
        validator = DataValidator(str(self.valid_file), "DOC001")
        json_str = validator.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        self.assertEqual(parsed["document_id"], "DOC001")
        self.assertEqual(parsed["standardized_data"]["validation"]["status"], "SUCCESS")

    def test_save_result_method(self):
        """Test saving validation result to file."""
        output_file = self.test_dir / "result.json"
        validator = DataValidator(str(self.valid_file), "DOC001")
        validator.save_result(str(output_file))

        self.assertTrue(output_file.exists())
        with open(output_file, 'r') as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data["document_id"], "DOC001")

    def test_error_handling_in_validation(self):
        """Test error handling during validation."""
        # Mock an exception in file checking
        with patch.object(DataValidator, 'check_file_exists', side_effect=Exception("Test error")):
            validator = DataValidator(str(self.valid_file))
            result = validator.validate()

            self.assertEqual(result["standardized_data"]["validation"]["status"], "VALIDATION_ERROR")
            self.assertIn("Test error", result["standardized_data"]["summary"]["errors"])

    def test_file_info_caching(self):
        """Test that file info is cached properly."""
        validator = DataValidator(str(self.valid_file))

        # First call should cache
        info1 = validator._get_file_info()
        # Second call should use cache
        info2 = validator._get_file_info()

        self.assertEqual(info1, info2)
        self.assertTrue(info1["exists"])
        self.assertEqual(info1["size"], len(self.sample_content))

    def test_metadata_in_result(self):
        """Test that metadata is properly included in results."""
        validator = DataValidator(str(self.valid_file), "DOC001", "Test System", "2.0")
        result = validator.validate()

        metadata = result["standardized_data"]["metadata"]
        self.assertEqual(metadata["processed_by"], "Test System")
        self.assertEqual(metadata["version"], "2.0")
        self.assertEqual(metadata["validator_class"], "DataValidator")
        self.assertIn("timestamp", metadata)

    def test_document_id_generation(self):
        """Test automatic document ID generation."""
        validator = DataValidator(str(self.valid_file))
        doc_id = validator.document_id

        self.assertTrue(doc_id.startswith("DOC"))
        self.assertEqual(len(doc_id), 23)  # DOC + 20 digit timestamp

    def test_file_details_in_result(self):
        """Test that file details are correctly populated."""
        validator = DataValidator(str(self.valid_file), "DOC001")
        result = validator.validate()

        details = result["standardized_data"]["file_details"]
        self.assertEqual(details["file_path"], str(self.valid_file))
        self.assertEqual(details["file_type"], "text")
        self.assertIsInstance(details["size_bytes"], int)
        self.assertGreater(details["size_bytes"], 0)
        self.assertIn("created_at", details)
        self.assertIn("last_modified", details)


class TestValidatorIntegration(unittest.TestCase):
    """Integration tests for validator with real file system."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_various_file_types(self):
        """Test validation of different file types."""
        test_files = [
            ("test.txt", "text", "Hello World"),
            ("test.json", "json", '{"key": "value"}'),
            ("test.xml", "xml", "<root><item>test</item></root>"),
            ("test.py", "code", "print('hello')"),
            ("test.yml", "config", "key: value"),
        ]

        for filename, expected_type, content in test_files:
            with self.subTest(filename=filename):
                test_file = self.test_dir / filename
                test_file.write_text(content)

                validator = DataValidator(str(test_file))
                result = validator.validate()

                self.assertEqual(result["standardized_data"]["validation"]["status"], "SUCCESS")
                self.assertEqual(result["standardized_data"]["file_details"]["file_type"], expected_type)


class TestStandardizedDataValidator(unittest.TestCase):
    """Test cases for StandardizedDataValidator."""

    def test_standardized_payload_success(self):
        payload = {
            "document_id": "DOC001",
            "standardized_data": {
                "file_details": {
                    "file_path": "data/raw/sample.txt",
                    "file_type": "text",
                    "created_at": "2026-04-10 12:45:00"
                },
                "validation": {
                    "file_exists": True,
                    "file_not_empty": True,
                    "file_readable": True,
                    "status": "SUCCESS"
                },
                "summary": {
                    "message": "Validation completed successfully",
                    "errors": None
                },
                "metadata": {
                    "processed_by": "RAG Validation System",
                    "version": "1.0",
                    "timestamp": "2026-04-10 12:45:00"
                }
            }
        }

        validator = StandardizedDataValidator(payload)
        result = validator.validate()

        self.assertTrue(result["validation_passed"])
        self.assertEqual(result["document_id"], "DOC001")
        self.assertEqual(result["schema_errors"], [])
        self.assertEqual(result["business_rule_violations"], [])

    def test_standardized_payload_schema_error(self):
        payload = {
            "document_id": "DOC001",
            "standardized_data": {
                "file_details": {
                    "file_path": "data/raw/sample.txt",
                    "file_type": "text"
                },
                "validation": {
                    "file_exists": True,
                    "file_not_empty": True,
                    "file_readable": True,
                    "status": "SUCCESS"
                },
                "summary": {
                    "message": "Validation completed successfully",
                    "errors": None
                },
                "metadata": {
                    "processed_by": "RAG Validation System",
                    "version": "1.0",
                    "timestamp": "2026-04-10 12:45:00"
                }
            }
        }

        validator = StandardizedDataValidator(payload)
        result = validator.validate()

        self.assertFalse(result["validation_passed"])
        self.assertIn("Missing required key 'created_at' in file_details", result["schema_errors"])

    def test_standardized_payload_business_rule_violation(self):
        payload = {
            "document_id": "DOC002",
            "standardized_data": {
                "file_details": {
                    "file_path": "data/raw/sample.txt",
                    "file_type": "text",
                    "created_at": "2026-04-10 12:45:00"
                },
                "validation": {
                    "file_exists": True,
                    "file_not_empty": True,
                    "file_readable": True,
                    "status": "FILE_NOT_FOUND"
                },
                "summary": {
                    "message": "Validation completed successfully",
                    "errors": "Should be failure"
                },
                "metadata": {
                    "processed_by": "RAG Validation System",
                    "version": "1.0",
                    "timestamp": "2026-04-10 12:45:00"
                }
            }
        }

        validator = StandardizedDataValidator(payload)
        result = validator.validate()

        self.assertFalse(result["validation_passed"])
        self.assertTrue(result["business_rule_violations"])
        self.assertIn("Status 'FILE_NOT_FOUND' requires file_exists=False", result["business_rule_violations"][0])

class TestStandardizedDataValidator(unittest.TestCase):
    """Tests for standardized payload and business rule validation."""

    def test_valid_standardized_payload(self):
        payload = {
            "document_id": "DOC001",
            "standardized_data": {
                "file_details": {
                    "file_path": "data/raw/sample.txt",
                    "file_type": "text",
                    "created_at": "2026-04-10 12:45:00"
                },
                "validation": {
                    "file_exists": True,
                    "file_not_empty": True,
                    "file_readable": True,
                    "status": "SUCCESS"
                },
                "summary": {
                    "message": "Validation completed successfully",
                    "errors": None
                },
                "metadata": {
                    "processed_by": "RAG Validation System",
                    "version": "1.0",
                    "timestamp": "2026-04-10 12:45:00"
                }
            }
        }

        from src.validator import StandardizedDataValidator
        validator = StandardizedDataValidator(payload)
        result = validator.validate()

        self.assertTrue(result["validation_passed"])
        self.assertEqual(result["schema_errors"], [])
        self.assertEqual(result["business_rule_violations"], [])

    def test_missing_key_in_payload(self):
        payload = {
            "document_id": "DOC001",
            "standardized_data": {
                "file_details": {
                    "file_path": "data/raw/sample.txt",
                    "file_type": "text"
                },
                "validation": {
                    "file_exists": True,
                    "file_not_empty": True,
                    "status": "SUCCESS"
                },
                "summary": {
                    "message": "Validation completed successfully",
                    "errors": None
                },
                "metadata": {
                    "processed_by": "RAG Validation System",
                    "version": "1.0",
                    "timestamp": "2026-04-10 12:45:00"
                }
            }
        }

        from src.validator import StandardizedDataValidator
        validator = StandardizedDataValidator(payload)
        result = validator.validate()

        self.assertFalse(result["validation_passed"])
        self.assertIn("Missing required key 'created_at' in file_details", result["schema_errors"])

    def test_business_rule_violation_when_status_mismatch(self):
        payload = {
            "document_id": "DOC001",
            "standardized_data": {
                "file_details": {
                    "file_path": "data/raw/sample.txt",
                    "file_type": "text",
                    "created_at": "2026-04-10 12:45:00"
                },
                "validation": {
                    "file_exists": False,
                    "file_not_empty": True,
                    "file_readable": False,
                    "status": "FILE_NOT_FOUND"
                },
                "summary": {
                    "message": "File not found",
                    "errors": "Missing file"
                },
                "metadata": {
                    "processed_by": "RAG Validation System",
                    "version": "1.0",
                    "timestamp": "2026-04-10 12:45:00"
                }
            }
        }

        from src.validator import StandardizedDataValidator
        validator = StandardizedDataValidator(payload)
        result = validator.validate()

        self.assertFalse(result["validation_passed"])
        self.assertIn("file_not_empty cannot be true when file_exists is false", result["business_rule_violations"])


def run_tests():
    """Run all tests with verbose output."""
    print("🧪 Running RAG Validation System Tests...\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestDataValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestValidatorIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print(f"\n📊 Test Results: {result.testsRun} tests run")
    if result.wasSuccessful():
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {len(result.failures)} failures, {len(result.errors)} errors")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    exit(exit_code)