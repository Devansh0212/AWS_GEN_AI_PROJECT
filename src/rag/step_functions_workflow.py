import os
import sys
import json
from datetime import datetime
from typing import Dict, List
import boto3
from botocore.exceptions import ClientError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.logger import get_logger

logger = get_logger("step_functions")

class StepFunctionsWorkflowOrchestrator:
    """
    Simulates an AWS Step Functions State Machine for Document Approval & Parallel RAG Ingestion.
    """
    def __init__(self, state_machine_arn: str = "arn:aws:states:us-east-1:866865535007:stateMachine:EnterpriseDocApprovalWorkflow"):
        self.state_machine_arn = os.getenv("STATE_MACHINE_ARN", state_machine_arn)
        
        try:
            self.sfn_client = boto3.client("stepfunctions", region_name="us-east-1")
            self.mock_mode = False
        except Exception as e:
            logger.warning(f"Could not initialize Step Functions boto3 client ({e}). Using local StateMachine fallback.")
            self.sfn_client = None
            self.mock_mode = True

    def execute_workflow(self, document_name: str, department: str = "HR", is_manager_approved: bool = True) -> Dict:
        """
        Executes Step Functions State Machine:
        Task State (Audit Scan) -> Choice State (Human Manager Approval) -> Parallel State (Bedrock Embeddings + DynamoDB Metadata).
        """
        execution_id = f"exec-{int(datetime.utcnow().timestamp())}"
        logger.info(f"[Step Functions] Starting State Machine Execution '{execution_id}' for '{document_name}'...")
        
        # 1. TASK STATE: Virus & PII Audit Scan
        logger.info(f"[Step 1: Task State] Performing Virus & PII Audit Scan on '{document_name}'...")
        if "infected" in document_name.lower():
            logger.error("[Step 1 Failed] Virus detected! Failing workflow state machine.")
            return {
                "execution_id": execution_id,
                "status": "FAILED",
                "failed_state": "Step_1_Audit_Scan",
                "error": "SecurityViolation: File infected with malware."
            }
            
        # 2. CHOICE STATE: Human Manager Approval Wait Check
        logger.info(f"[Step 2: Choice State] Checking Manager Approval Status (Approved: {is_manager_approved})...")
        if not is_manager_approved:
            logger.warning("[Step 2 Rejected] Manager rejected document approval. Ending workflow.")
            return {
                "execution_id": execution_id,
                "status": "FAILED",
                "failed_state": "Step_2_Choice_Approval",
                "error": "ApprovalRejected: Manager declined document ingestion."
            }
            
        # 3. PARALLEL STATE: Execute Branch A (Bedrock Vector Ingestion) + Branch B (DynamoDB Metadata)
        logger.info(f"[Step 3: Parallel State] Spawning Branch A (Bedrock Vector Store) & Branch B (DynamoDB Metadata)...")
        branch_a_res = {
            "branch": "Branch_A_Bedrock_Embeddings",
            "status": "completed",
            "chunks_embedded": 4,
            "vector_store": "OpenSearch_Serverless"
        }
        
        branch_b_res = {
            "branch": "Branch_B_DynamoDB_Metadata",
            "status": "completed",
            "table_name": "EnterpriseDocumentMetadata",
            "recorded_at": datetime.utcnow().isoformat() + "Z"
        }
        
        logger.info("[Step Functions Completed] Workflow executed all states successfully!")
        return {
            "execution_id": execution_id,
            "status": "SUCCEEDED",
            "document_name": document_name,
            "department": department,
            "parallel_execution_results": [branch_a_res, branch_b_res]
        }

if __name__ == "__main__":
    orchestrator = StepFunctionsWorkflowOrchestrator()
    
    # Execution 1: Successful Approved Document Workflow
    res1 = orchestrator.execute_workflow("2026_executive_strategy.pdf", department="Executive", is_manager_approved=True)
    print("--- Step Functions Execution 1 (Approved Workflow) ---")
    print(json.dumps(res1, indent=2))
    
    # Execution 2: Rejected Document Workflow
    res2 = orchestrator.execute_workflow("unauthorized_draft.pdf", department="Finance", is_manager_approved=False)
    print("\n--- Step Functions Execution 2 (Rejected Workflow) ---")
    print(json.dumps(res2, indent=2))
