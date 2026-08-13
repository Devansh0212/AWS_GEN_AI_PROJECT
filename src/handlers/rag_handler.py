import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.logger import get_logger
from src.rag.rag_engine import CustomRAGEngine
from src.rag.session_memory import DynamoDBSessionMemory

logger = get_logger("rag_handler")

# Instantiate Custom RAG Engine and Session Memory
rag_engine = CustomRAGEngine()
session_memory = DynamoDBSessionMemory()

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
    session_id = body.get("session_id", event.get("session_id", "default-session"))
    
    if not question:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing required field: 'question'"})
        }
        
    # Read environment variables
    environment = os.getenv("APP_ENV", "development")
    
    # 1. Fetch Session History from DynamoDB
    history = session_memory.get_history(session_id)
    
    # 2. Execute Grounded RAG Query Pipeline with History
    rag_result = rag_engine.query(question, chat_history=history)
    answer = rag_result.get("answer", "")
    
    # 3. Save new turn to DynamoDB Session Memory
    session_memory.add_turn(session_id=session_id, user_query=question, assistant_response=answer)
    
    response_payload = {
        "status": "success",
        "environment": environment,
        "session_id": session_id,
        "question": question,
        "answer": answer,
        "sources": rag_result.get("sources", []),
        "history_turns_count": len(history) // 2,
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
