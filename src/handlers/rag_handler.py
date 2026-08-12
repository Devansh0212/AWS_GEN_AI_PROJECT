import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.logger import get_logger
from src.rag.bedrock_llm import BedrockLLM

logger = get_logger("rag_handler")

# Instantiate Bedrock LLM wrapper
llm_client = BedrockLLM()

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
    
    # Invoke Amazon Bedrock Foundation Model
    system_prompt = "You are a professional enterprise knowledge assistant. Answer the user's question clearly and concisely."
    llm_result = llm_client.generate_response(prompt=question, system_prompt=system_prompt)
    
    response_payload = {
        "status": "success",
        "environment": environment,
        "question": question,
        "answer": llm_result.get("response_text", llm_result.get("fallback_response")),
        "model_id": llm_result.get("model_id"),
        "usage": llm_result.get("usage"),
        "is_rag_grounded": False  # Explicitly marking that this endpoint is direct LLM inference (RAG coming in Phase 8/9!)
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
