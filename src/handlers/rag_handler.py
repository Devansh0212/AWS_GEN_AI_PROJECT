import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.logger import get_logger
from src.rag.rag_engine import CustomRAGEngine

logger = get_logger("rag_handler")

# Instantiate Custom RAG Engine
rag_engine = CustomRAGEngine()

def lambda_handler(event: dict, context) -> dict:
    """
    AWS Lambda entry point for RAG Conversational Knowledge Assistant.
    """
    logger.info(f"Received Lambda event: {json.dumps(event)}")
    
    # Extract query parameters or JSON body
    body = {}
    if "body" in event and event["body"]:
        if isinstance(event["body"], str):
            body = json.loads(event["body"])
        else:
            body = event["body"]
            
    question = body.get("question", event.get("question", ""))
    
    if not question:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing required field: 'question'"})
        }
        
    # Read environment variables
    environment = os.getenv("APP_ENV", "development")
    
    # Execute Grounded RAG Query Pipeline
    rag_result = rag_engine.query(question)
    
    response_payload = {
        "status": "success",
        "environment": environment,
        "question": question,
        "answer": rag_result.get("answer"),
        "sources": rag_result.get("sources", []),
        "retrieved_chunks_count": len(rag_result.get("retrieved_context", [])),
        "is_rag_grounded": True
    }
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(response_payload)
    }

if __name__ == "__main__":
    # Local simulation test
    test_event = {
        "body": json.dumps({"question": "What is the vacation policy for contractors?"})
    }
    result = lambda_handler(test_event, None)
    print("--- Lambda Handler Local Test Response ---")
    print(json.dumps(result, indent=2))
