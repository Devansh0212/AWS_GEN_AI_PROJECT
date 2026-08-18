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

class EventBridgeEventRouter:
    """
    Event-Driven Architecture Router using Amazon EventBridge.
    """
    def __init__(self, bus_name: str = "default", region_name: str = "us-east-1"):
        self.bus_name = bus_name
        self.region_name = region_name
        
        try:
            self.events_client = boto3.client("events", region_name=self.region_name)
            self.mock_mode = False
        except Exception as e:
            logger.warning(f"Could not initialize boto3 events client ({e}). Running in simulation mode.")
            self.events_client = None
            self.mock_mode = True

    def publish_event(self, source: str, detail_type: str, detail: Dict) -> Dict:
        """
        Publishes a custom JSON event payload to the EventBridge Event Bus.
        """
        event_entry = {
            "Source": source,
            "DetailType": detail_type,
            "Detail": json.dumps(detail),
            "EventBusName": self.bus_name,
            "Time": datetime.utcnow()
        }
        
        logger.info(f"[EventBridge Bus] Publishing event '{detail_type}' from source '{source}'...")
        
        if self.mock_mode or not self.events_client:
            return self._route_simulated_event(source, detail_type, detail)
            
        try:
            response = self.events_client.put_events(Entries=[event_entry])
            failed_count = response.get("FailedEntryCount", 0)
            if failed_count > 0:
                logger.warning("EventBridge PutEvents failed entry count > 0. Using router fallback.")
                return self._route_simulated_event(source, detail_type, detail)
            
            entry = response.get("Entries", [{}])[0]
            return {
                "status": "published_eventbridge",
                "event_id": entry.get("EventId"),
                "routing": self._route_simulated_event(source, detail_type, detail)["routing"]
            }
        except ClientError as e:
            logger.warning(f"EventBridge Error: {e}. Using router fallback.")
            return self._route_simulated_event(source, detail_type, detail)

    def _route_simulated_event(self, source: str, detail_type: str, detail: Dict) -> Dict:
        """
        EventPattern Rule Router: Matches event rules and determines target destination.
        """
        routing_info = {}
        
        if detail_type == "Object Created":
            routing_info = {
                "matched_rule": "Rule_S3_Document_Created",
                "target_service": "Amazon SQS Queue (EnterpriseDocIngestionQueue)",
                "action": "Enqueue document for batch chunking & embedding generation"
            }
        elif detail_type == "Object Removed":
            routing_info = {
                "matched_rule": "Rule_S3_Document_Deleted",
                "target_service": "AWS Lambda (DeleteVectorEmbeddingsHandler)",
                "action": "Purge deleted document chunks from Vector Database"
            }
        elif detail_type == "Guardrail Violation":
            routing_info = {
                "matched_rule": "Rule_Security_Attack_Detected",
                "target_service": "Amazon SNS / CloudWatch Alarms",
                "action": "Trigger high-priority DevOps security alert"
            }
        else:
            routing_info = {
                "matched_rule": "Default_Fallback_Rule",
                "target_service": "CloudWatch Logs",
                "action": "Log event payload"
            }
            
        return {
            "status": "event_routed",
            "source": source,
            "detail_type": detail_type,
            "routing": routing_info
        }

if __name__ == "__main__":
    router = EventBridgeEventRouter()
    
    # Event 1: File Uploaded
    e1 = router.publish_event("aws.s3", "Object Created", {"bucket": "enterprise-docs", "key": "hr/handbook.pdf"})
    print("--- EventBridge Event 1: Document Uploaded ---")
    print(json.dumps(e1, indent=2))
    
    # Event 2: File Deleted
    e2 = router.publish_event("aws.s3", "Object Removed", {"bucket": "enterprise-docs", "key": "hr/old_policy.pdf"})
    print("\n--- EventBridge Event 2: Document Deleted ---")
    print(json.dumps(e2, indent=2))
    
    # Event 3: Security Guardrail Blocked
    e3 = router.publish_event("enterprise.rag.security", "Guardrail Violation", {"attack_type": "Prompt Injection", "user": "user101"})
    print("\n--- EventBridge Event 3: Security Guardrail Violation ---")
    print(json.dumps(e3, indent=2))
