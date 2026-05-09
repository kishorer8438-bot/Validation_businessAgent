"""
AI Helper Script for RAG Validation System

This script provides AI-powered explanations for validation errors using Cohere and Google Gemini.
Designed for production use with comprehensive error handling, logging, and configuration management.

Author: Professional Python Developer
Version: 2.1.0
"""

import os
import sys
import logging
import argparse
from typing import List, Optional, Dict, Any, Literal
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

import cohere

try:
    import google.genai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        import google.generativeai as genai  # Fallback to deprecated package
        GEMINI_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class AIProvider(Enum):
    """Supported AI providers."""
    COHERE = "cohere"
    GEMINI = "gemini"


# Configuration
@dataclass
class AIHelperConfig:
    """Configuration for AI Helper service."""
    provider: AIProvider
    api_key: str
    model: str = "command-r-plus-08-2024"
    max_retries: int = 3
    timeout: int = 30
    temperature: float = 0.7
    max_tokens: int = 1000

    @classmethod
    def from_env(cls, provider: AIProvider = AIProvider.COHERE, api_key: Optional[str] = None) -> 'AIHelperConfig':
        """Create configuration from environment variables or provided API key."""

        if provider == AIProvider.COHERE:
            api_key = api_key or os.getenv('COHERE_API_KEY')
            default_model = os.getenv('COHERE_MODEL', 'command-r-plus-08-2024')
            if not api_key:
                raise APIKeyError(
                    'Cohere API key is required. Provide it via --api-key or COHERE_API_KEY.'
                )
        elif provider == AIProvider.GEMINI:
            api_key = api_key or os.getenv('GOOGLE_API_KEY')
            default_model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
            if not api_key:
                raise APIKeyError(
                    'Google API key is required. Provide it via --api-key or GOOGLE_API_KEY.'
                )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        return cls(
            provider=provider,
            api_key=api_key,
            model=default_model,
            max_retries=int(os.getenv('AI_MAX_RETRIES', '3')),
            timeout=int(os.getenv('AI_TIMEOUT', '30')),
            temperature=float(os.getenv('AI_TEMPERATURE', '0.7')),
            max_tokens=int(os.getenv('AI_MAX_TOKENS', '1000'))
        )


class AIHelperError(Exception):
    """Base exception for AI Helper operations."""
    pass


class APIKeyError(AIHelperError):
    """Raised when API key is invalid or missing."""
    pass


class APIError(AIHelperError):
    """Raised when API calls fail."""
    pass


class AIHelperService:
    """
    Professional AI Helper service for generating validation error explanations.

    Features:
    - Robust error handling with retries
    - Comprehensive logging
    - Type-safe interfaces
    - Production-ready configuration
    """

    def __init__(self, config: AIHelperConfig):
        """
        Initialize the AI Helper service.

        Args:
            config: Service configuration

        Raises:
            APIKeyError: If API key is invalid
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        try:
            if config.provider == AIProvider.COHERE:
                self.client = cohere.Client(api_key=config.api_key)
                self.logger.info("Cohere AI Helper service initialized successfully")
            elif config.provider == AIProvider.GEMINI:
                if not GEMINI_AVAILABLE:
                    raise ImportError("Google Generative AI library not available. Install with: pip install google-genai")
                # Try new API first, fallback to old API
                try:
                    import google.genai as genai_new
                    self.client = genai_new.Client(api_key=config.api_key)
                    self.genai_model = genai_new.GenerativeModel(config.model)
                    self.logger.info("Gemini AI Helper service initialized successfully (new API)")
                except (AttributeError, ImportError):
                    # Fallback to old deprecated API
                    import google.generativeai as genai_old
                    genai_old.configure(api_key=config.api_key)
                    self.client = genai_old.GenerativeModel(config.model)
                    self.logger.info("Gemini AI Helper service initialized successfully (legacy API)")
            else:
                raise ValueError(f"Unsupported AI provider: {config.provider}")
        except Exception as e:
            self.logger.error(f"Failed to initialize {config.provider.value} client: {e}")
            raise APIKeyError(f"Invalid API key for {config.provider.value}: {e}") from e

    def _build_prompt(self, errors: List[str]) -> str:
        """
        Build a comprehensive prompt for error explanation.

        Args:
            errors: List of validation error messages

        Returns:
            Formatted prompt string
        """
        error_text = "\n".join(f"- {error}" for error in errors)

        return f"""You are an expert software validation consultant with 10+ years of experience.
Please analyze these validation errors and provide clear, actionable explanations:

VALIDATION ERRORS:
{error_text}

Please provide:
1. A clear explanation of what each error means
2. The likely root cause of each error
3. Specific, actionable steps to fix each error
4. Best practices to prevent similar errors in the future
5. Any additional context that would help developers understand and resolve these issues

Format your response professionally with clear headings and bullet points."""

    def _validate_input(self, errors: List[str]) -> None:
        """
        Validate input parameters.

        Args:
            errors: List of error messages to validate

        Raises:
            ValueError: If input is invalid
        """
        if not errors:
            raise ValueError("Error list cannot be empty")

        if not isinstance(errors, list):
            raise ValueError("Errors must be provided as a list")

        if not all(isinstance(error, str) for error in errors):
            raise ValueError("All errors must be strings")

        if any(not error.strip() for error in errors):
            raise ValueError("Error messages cannot be empty or whitespace-only")

        placeholders = [
            "your validation error here",
            "example validation error",
            "test error",
            "placeholder error",
        ]

        lower_errors = [error.strip().lower() for error in errors if isinstance(error, str)]
        if any(lower_error == placeholder for lower_error in lower_errors for placeholder in placeholders):
            raise ValueError(
                "Please provide a real validation error message instead of placeholder text. "
                "For example: \"Amount must be > 0\" or \"Email format is invalid\"."
            )

    def explain_errors(self, errors: List[str]) -> str:
        """
        Generate AI-powered explanations for validation errors.

        Args:
            errors: List of validation error messages

        Returns:
            Comprehensive explanation with fixes and recommendations

        Raises:
            AIHelperError: If explanation generation fails
        """
        self._validate_input(errors)
        self.logger.info(f"Generating explanation for {len(errors)} validation errors")

        prompt = self._build_prompt(errors)

        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(f"API call attempt {attempt + 1}/{self.config.max_retries}")

                if self.config.provider == AIProvider.COHERE:
                    response = self.client.chat(
                        model=self.config.model,
                        message=prompt,
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens
                    )
                    response_text = response.text

                elif self.config.provider == AIProvider.GEMINI:
                    # Use the legacy API for now (still supported)
                    response = self.client.generate_content(
                        prompt,
                        generation_config={
                            "temperature": self.config.temperature,
                            "max_output_tokens": self.config.max_tokens,
                        }
                    )
                    response_text = response.text if hasattr(response, 'text') and response.text else ""

                if not response_text:
                    raise APIError("Empty response from AI service")

                self.logger.info("Successfully generated error explanation")
                return response_text.strip()

            except Exception as e:
                # Handle provider-specific errors
                if self.config.provider == AIProvider.COHERE:
                    if isinstance(e, cohere.UnauthorizedError):
                        error_msg = f"Invalid API key (attempt {attempt + 1}): {e}"
                        self.logger.error(error_msg)
                        if attempt == self.config.max_retries - 1:
                            raise APIKeyError("Invalid Cohere API key. Please check your COHERE_API_KEY environment variable.") from e
                    elif isinstance(e, (cohere.BadRequestError, cohere.ForbiddenError,
                                      cohere.NotFoundError, cohere.TooManyRequestsError, cohere.InternalServerError)):
                        error_msg = f"Cohere API error (attempt {attempt + 1}): {e}"
                        self.logger.warning(error_msg)
                        if attempt == self.config.max_retries - 1:
                            raise APIError(f"Cohere service unavailable after {self.config.max_retries} attempts: {e}") from e
                    else:
                        error_msg = f"Unexpected Cohere error (attempt {attempt + 1}): {e}"
                        self.logger.error(error_msg)
                        if attempt == self.config.max_retries - 1:
                            raise AIHelperError(f"Failed to generate explanation with Cohere: {e}") from e

                elif self.config.provider == AIProvider.GEMINI:
                    error_msg = f"Gemini API error (attempt {attempt + 1}): {e}"
                    self.logger.warning(error_msg)
                    if attempt == self.config.max_retries - 1:
                        raise APIError(f"Gemini service unavailable after {self.config.max_retries} attempts: {e}") from e

        # This should never be reached, but just in case
        raise AIHelperError("Maximum retry attempts exceeded")


def setup_logging(verbose: bool = False) -> None:
    """Setup comprehensive logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/ai_helper.log', mode='a')
        ]
    )


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="AI Helper - Generate explanations for validation errors using Cohere or Gemini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ai_helper.py "Amount must be > 0" "Invalid email format"
  python ai_helper.py --provider gemini "Amount must be > 0"
  python ai_helper.py --api-key "your-api-key" --provider cohere "Amount must be > 0"
  python ai_helper.py --verbose --errors-file errors.txt
        """
    )

    parser.add_argument(
        'errors',
        nargs='*',
        help='Validation error messages to explain'
    )

    parser.add_argument(
        '--provider', '-p',
        choices=['cohere', 'gemini'],
        default='cohere',
        help='AI provider to use (default: cohere)'
    )

    parser.add_argument(
        '--errors-file', '-f',
        type=Path,
        help='File containing error messages (one per line)'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output file for explanation (default: stdout)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--api-key',
        help='API key (optional when environment variables are set)'
    )

    parser.add_argument(
        '--model',
        help='Model to use (optional, uses provider default)'
    )

    return parser


def load_errors_from_file(file_path: Path) -> List[str]:
    """Load error messages from a file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Errors file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        errors = [line.strip() for line in f if line.strip()]

    if not errors:
        raise ValueError(f"No valid error messages found in {file_path}")

    return errors


def main() -> int:
    """Main entry point with comprehensive error handling."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    try:
        # Determine AI provider
        provider = AIProvider.COHERE if args.provider == 'cohere' else AIProvider.GEMINI

        # Load configuration
        config = AIHelperConfig.from_env(provider=provider, api_key=args.api_key)

        # Override config from args if provided
        if args.model:
            config.model = args.model

        # Initialize service
        service = AIHelperService(config)

        # Load errors
        if args.errors_file:
            errors = load_errors_from_file(args.errors_file)
        elif args.errors:
            errors = args.errors
        else:
            parser.print_usage(sys.stderr)
            raise ValueError(
                'No validation errors provided. Pass errors as positional arguments or use --errors-file.'
            )

        # Generate explanation
        explanation = service.explain_errors(errors)

        # Output result
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(explanation)
            print(f"Explanation written to {args.output}")
        else:
            print("AI-GENERATED EXPLANATION:")
            print("=" * 50)
            print(explanation)
            print("=" * 50)

        return 0

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130

    except AIHelperError as e:
        print(f"AI Helper Error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        logging.exception("Unhandled exception")
        return 1


if __name__ == "__main__":
    sys.exit(main())