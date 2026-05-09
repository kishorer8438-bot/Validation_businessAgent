import json
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Define the state
class ValidationState(TypedDict):
    input_json: Dict[str, Any]
    validation_result: str
    output_json: Dict[str, Any]

# Example output format
example_output = {
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
            "processed_by": "RAG Validation System with LangGraph",
            "version": "2.0",
            "timestamp": "2026-04-25 12:00:00"
        }
    }
}

def validate_node(state: ValidationState) -> ValidationState:
    input_json = state['input_json']
    prompt = f"""
    Validate the following JSON data: {json.dumps(input_json)}.
    Check if it represents valid file details for a document validation system.
    Specifically:
    - Does it have file_path, file_type, created_at?
    - Is the file_path valid?
    - Would the file exist based on typical checks?
    Provide a detailed validation assessment.
    """
    # Get LLM from global (will be set in validate_with_langgraph)
    response = llm.invoke(prompt)
    state['validation_result'] = response.content
    return state

def generate_output_node(state: ValidationState) -> ValidationState:
    validation = state['validation_result']
    input_json = state['input_json']
    prompt = f"""
    Based on the validation assessment: {validation}
    And the input JSON: {json.dumps(input_json)}
    Generate an output JSON in the exact format as this example: {json.dumps(example_output)}
    Ensure the output is valid JSON and matches the structure.
    Set the status to SUCCESS if validation passes, FAILED otherwise.
    Include appropriate message and errors.
    Use current timestamp.
    """
    # Get LLM from global
    response = llm.invoke(prompt)
    # Extract JSON from response
    content = response.content.strip()
    if content.startswith('```json'):
        content = content[7:-3].strip()
    try:
        output = json.loads(content)
        state['output_json'] = output
    except json.JSONDecodeError:
        # Fallback
        state['output_json'] = example_output
    return state

def validate_with_langgraph(input_data: Dict[str, Any]) -> Dict[str, Any]:
    # Initialize LLM here to avoid import-time errors
    global llm
    llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0)
    
    # Build the graph
    graph = StateGraph(ValidationState)
    graph.add_node("validate", validate_node)
    graph.add_node("generate_output", generate_output_node)
    graph.add_edge("validate", "generate_output")
    graph.add_edge("generate_output", END)
    graph.set_entry_point("validate")

    # Compile the graph
    langgraph_app = graph.compile()
    
    result = langgraph_app.invoke({"input_json": input_data, "validation_result": "", "output_json": {}})
    return result['output_json']