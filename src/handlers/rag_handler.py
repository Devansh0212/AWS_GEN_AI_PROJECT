import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.logger import get_logger

logger = get_logger("rag_handler")

def lambda_handler(event: dict, context) -> dict:
    """
    AWS Lambda entry point for RAG Conversational Knowledge Assistant.
    
    Parameters:
        event (dict): Incoming AWS event payload (from API Gateway, test events, etc.)
        context (LambdaContext): AWS runtime metadata (request ID, remaining time, etc.)
        
    Returns:
        dict: Standard HTTP response dictionary containing statusCode, headers, and JSON body.
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
    s3_bucket = os.getenv("S3_BUCKET_NAME", "enterprise-rag-docs-default")
    
    # Simulated processing logic (Pre-Bedrock integration)
    response_payload = {
        "status": "success",
        "environment": environment,
        "bucket_configured": s3_bucket,
        "received_question": question,
        "message": f"Lambda received your question: '{question}'. Bedrock integration coming in Phase 6!"
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
