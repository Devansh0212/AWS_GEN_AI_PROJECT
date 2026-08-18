import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.logger import get_logger
from src.agent.langgraph_agent import LangGraphRAGAgent
from src.rag.session_memory import DynamoDBSessionMemory

logger = get_logger("rag_handler")

# Instantiate LangGraph Agent and DynamoDB Session Memory
agent = LangGraphRAGAgent()
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
    
    # 2. Execute Stateful LangGraph Agent Machine
    agent_result = agent.run(question, session_id=session_id)
    answer = agent_result.get("answer", "")
    
    # 3. Save new turn to DynamoDB Session Memory if not blocked
    if agent_result.get("status") != "blocked_by_guardrail":
        session_memory.add_turn(session_id=session_id, user_query=question, assistant_response=answer)
    
    response_payload = {
        "status": agent_result.get("status", "success"),
        "environment": environment,
        "session_id": session_id,
        "question": question,
        "answer": answer,
        "sources": agent_result.get("sources", []),
        "history_turns_count": len(history) // 2,
        "is_rag_grounded": agent_result.get("is_rag_grounded", False),
        "orchestrator": "LangGraph"
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
