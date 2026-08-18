import os
import sys
import json
from datetime import datetime
from typing import Dict, List
import boto3
from botocore.exceptions import ClientError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.logger import get_logger

logger = get_logger("eventbridge_router")

class EventBridgeRouter:
    """
    Serverless Event Bus Router demonstrating Amazon EventBridge event patterns & target dispatching.
    """
    def __init__(self, event_bus_name: str = "EnterpriseEventBus"):
        self.event_bus_name = os.getenv("EVENT_BUS_NAME", event_bus_name)
        
        try:
            self.eventbridge_client = boto3.client("events", region_name="us-east-1")
            self.mock_mode = False
        except Exception as e:
            logger.warning(f"Could not initialize EventBridge boto3 client ({e}). Using local EventBus fallback.")
            self.eventbridge_client = None
            self.mock_mode = True

    def publish_event(self, source: str, detail_type: str, detail: Dict) -> Dict:
        """
        Publishes a JSON event entry to the EventBridge Event Bus.
        """
        event_entry = {
            "Time": datetime.utcnow(),
            "Source": source,
            "DetailType": detail_type,
            "Detail": json.dumps(detail),
            "EventBusName": self.event_bus_name
        }
        
        logger.info(f"[EventBridge] Publishing event '{detail_type}' from '{source}' to bus '{self.event_bus_name}'...")
        
        # Local Rule Evaluation Simulation
        triggered_targets = self._evaluate_event_rules(source, detail_type, detail)
        
        if self.mock_mode or not self.eventbridge_client:
            return {
                "status": "published_local",
                "event_bus": self.event_bus_name,
                "source": source,
                "detail_type": detail_type,
                "triggered_targets": triggered_targets
            }
            
        try:
            response = self.eventbridge_client.put_events(Entries=[event_entry])
            failed_count = response.get("FailedEntryCount", 0)
            return {
                "status": "published_eventbridge" if failed_count == 0 else "failed",
                "event_bus": self.event_bus_name,
                "triggered_targets": triggered_targets
            }
        except ClientError as e:
            logger.warning(f"EventBridge PutEvents Error [{e.response['Error']['Code']}]: Using local EventBus fallback.")
            return {
                "status": "published_local",
                "event_bus": self.event_bus_name,
                "triggered_targets": triggered_targets
            }

    def _evaluate_event_rules(self, source: str, detail_type: str, detail: Dict) -> List[str]:
        """
        Simulates EventBridge Rule pattern matching and target routing.
        """
        targets = []
        
        # Rule 1: Match HR Document Uploads -> Route to SQS Ingestion Queue
        if source == "enterprise.hr.app" and detail_type == "DocumentUploaded":
            targets.append("Target 1: SQS Ingestion Queue (RAG Indexer)")
            targets.append("Target 2: CloudWatch Compliance Audit Log")
            
        # Rule 2: Match Security Policy Updates -> Route to Step Functions Approval Workflow
        if "security" in detail.get("file_name", "").lower() or detail.get("department") == "Security":
            targets.append("Target 3: Step Functions Security Approval Workflow")
            
        return targets

if __name__ == "__main__":
    router = EventBridgeRouter()
    
    # Event 1: HR Vacation Policy Upload
    e1 = router.publish_event(
        source="enterprise.hr.app",
        detail_type="DocumentUploaded",
        detail={"file_name": "2026_vacation_policy.pdf", "department": "HR", "author": "Alice"}
    )
    print("--- Event 1 Routing Results (HR Document) ---")
    print(json.dumps(e1, indent=2))
    
    # Event 2: Security Compliance Document Upload
    e2 = router.publish_event(
        source="enterprise.hr.app",
        detail_type="DocumentUploaded",
        detail={"file_name": "security_compliance.pdf", "department": "Security", "author": "Bob"}
    )
    print("\n--- Event 2 Routing Results (Security Document) ---")
    print(json.dumps(e2, indent=2))
