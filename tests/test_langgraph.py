import json
import pytest
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
from src.langgraph_validator import validate_with_langgraph

def test_langgraph_validation():
    input_data = {
        "file_path": "data/raw/sample.txt",
        "file_type": "text",
        "created_at": "2026-04-10 12:45:00"
    }

    try:
        result = validate_with_langgraph(input_data)
        print("Input:", json.dumps(input_data, indent=2))
        print("Output:", json.dumps(result, indent=2))
    except ChatGoogleGenerativeAIError as e:
        pytest.skip(f"Gemini API error: {e}. Skipping test - please check your GOOGLE_API_KEY")

if __name__ == "__main__":
    test_langgraph_validation()