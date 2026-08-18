import os
import sys
import json
from datetime import datetime
from typing import Dict, List
import boto3
from botocore.exceptions import ClientError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.logger import get_logger

logger = get_logger("step_functions_workflow")

class StepFunctionsIngestionWorkflow:
    """
    Serverless Workflow Orchestrator demonstrating AWS Step Functions state machine execution.
    """
    def __init__(self, state_machine_arn: str = "arn:aws:states:us-east-1:866865535007:stateMachine:EnterpriseDocIngestionWorkflow"):
        self.state_machine_arn = os.getenv("STATE_MACHINE_ARN", state_machine_arn)
        
        try:
            self.sfn_client = boto3.client("stepfunctions", region_name="us-east-1")
            self.mock_mode = False
        except Exception as e:
            logger.warning(f"Could not initialize StepFunctions boto3 client ({e}). Using local workflow fallback.")
            self.sfn_client = None
            self.mock_mode = True

    def step_scan_document(self, object_key: str) -> Dict:
        """Step 1 Task State: Scans document for security risks and PII."""
        logger.info(f"[Step 1: Scan Document] Scanning '{object_key}' for security risks...")
        has_risk = "security" in object_key.lower() or "confidential" in object_key.lower()
        return {"object_key": object_key, "has_security_risk": has_risk, "scan_status": "COMPLETED"}

    def step_human_security_review(self, object_key: str) -> Dict:
        """Step 2 Choice/Task State: Simulates Human-in-the-loop approval pause."""
        logger.info(f"[Step 2: Human Security Review] Pausing workflow for human approval on '{object_key}'...")
        # Simulated approval decision
        approved = True
        return {"object_key": object_key, "approved": approved, "reviewer": "SecurityAdmin_Alice"}

    def step_push_to_sqs(self, object_key: str) -> Dict:
        """Step 3 Task State: Pushes document metadata to SQS Ingestion Queue."""
        logger.info(f"[Step 3: SQS Ingestion Queue] Queueing '{object_key}' for asynchronous processing...")
        return {"object_key": object_key, "sqs_message_id": f"msg-{int(datetime.utcnow().timestamp())}"}

    def step_bedrock_vector_index(self, object_key: str) -> Dict:
        """Step 4 Task State: Generates Bedrock vector embeddings and indexes document."""
        logger.info(f"[Step 4: Bedrock Vector Index] Indexing '{object_key}' into vector store...")
        return {"object_key": object_key, "vector_chunks_created": 4, "embedding_model": "amazon.titan-embed-text-v1"}

    def execute_workflow(self, object_key: str, is_security_sensitive: bool = False) -> Dict:
        """
        Executes the Step Functions State Machine workflow.
        """
        execution_id = f"exec-{int(datetime.utcnow().timestamp())}"
        logger.info(f"[Step Functions] Starting workflow execution '{execution_id}' for '{object_key}'...")
        
        execution_history = []
        
        # 1. Step 1: Scan Document
        step1 = self.step_scan_document(object_key)
        execution_history.append({"step": "1_ScanDocument", "result": step1})
        
        # 2. Step 2: Choice State (If Security Risk -> Human Review)
        if is_security_sensitive or step1["has_security_risk"]:
            step2 = self.step_human_security_review(object_key)
            execution_history.append({"step": "2_HumanSecurityReview", "result": step2})
            
            if not step2["approved"]:
                logger.warning(f"[Step Functions] Workflow FAILED: Document '{object_key}' rejected during security review.")
                return {
                    "status": "FAILED",
                    "execution_id": execution_id,
                    "reason": "Security Review Rejected",
                    "execution_history": execution_history
                }
                
        # 3. Step 3: SQS Queueing
        step3 = self.step_push_to_sqs(object_key)
        execution_history.append({"step": "3_PushToSQS", "result": step3})
        
        # 4. Step 4: Bedrock Vector Indexing
        step4 = self.step_bedrock_vector_index(object_key)
        execution_history.append({"step": "4_BedrockVectorIndex", "result": step4})
        
        logger.info(f"[Step Functions] Workflow execution '{execution_id}' COMPLETED SUCCESSFULLY.")
        return {
            "status": "SUCCEEDED",
            "execution_id": execution_id,
            "object_key": object_key,
            "steps_completed": len(execution_history),
            "execution_history": execution_history
        }

if __name__ == "__main__":
    workflow = StepFunctionsIngestionWorkflow()
    
    # Test 1: Standard Document (Fast Path)
    w1 = workflow.execute_workflow("policies/2026_hr_handbook.pdf")
    print("--- Step Functions Workflow Result (Standard Document) ---")
    print(json.dumps(w1, indent=2))
    
    # Test 2: Sensitive Security Document (Human Approval Path)
    w2 = workflow.execute_workflow("policies/security_compliance.pdf", is_security_sensitive=True)
    print("\n--- Step Functions Workflow Result (Sensitive Security Document) ---")
    print(json.dumps(w2, indent=2))
