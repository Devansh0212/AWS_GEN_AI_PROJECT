import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Optional
import boto3
from botocore.exceptions import ClientError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.logger import get_logger

logger = get_logger("session_memory")

class DynamoDBSessionMemory:
    """
    Manages conversational memory & multi-turn session state using Amazon DynamoDB.
    """
    def __init__(
        self,
        table_name: str = "EnterpriseRagSessions",
        region_name: str = "us-east-1",
        max_history_turns: int = 6
    ):
        self.table_name = os.getenv("DYNAMODB_TABLE_NAME", table_name)
        self.region_name = region_name
        self.max_history_turns = max_history_turns
        
        # Local in-memory fallback store for offline development
        self.local_memory_store: Dict[str, List[Dict]] = {}
        
        try:
            self.dynamodb = boto3.resource("dynamodb", region_name=self.region_name)
            self.table = self.dynamodb.Table(self.table_name)
            self.mock_mode = False
        except Exception as e:
            logger.warning(f"Could not connect to DynamoDB resource ({e}). Falling back to local session store.")
            self.dynamodb = None
            self.table = None
            self.mock_mode = True

    def get_history(self, session_id: str) -> List[Dict]:
        """
        Fetches multi-turn chat history for a session_id.
        """
        if self.mock_mode or not self.table:
            return self.local_memory_store.get(session_id, [])
            
        try:
            response = self.table.get_item(Key={"session_id": session_id})
            item = response.get("Item", {})
            history = item.get("history", [])
            logger.info(f"Retrieved {len(history)} past messages for session '{session_id}' from DynamoDB.")
            return history
        except ClientError as e:
            logger.warning(f"DynamoDB GetItem Error [{e.response['Error']['Code']}]: {e.response['Error']['Message']}. Using local fallback.")
            return self.local_memory_store.get(session_id, [])

    def add_turn(self, session_id: str, user_query: str, assistant_response: str):
        """
        Appends a new conversation turn (user + assistant) to DynamoDB session history.
        """
        current_history = self.get_history(session_id)
        
        # Append new turns
        current_history.append({"role": "user", "content": user_query})
        current_history.append({"role": "assistant", "content": assistant_response})
        
        # Enforce sliding window (keep last max_history_turns)
        if len(current_history) > self.max_history_turns:
            current_history = current_history[-self.max_history_turns:]
            
        if self.mock_mode or not self.table:
            self.local_memory_store[session_id] = current_history
            logger.info(f"[Local Session Memory] Updated '{session_id}': total stored turns = {len(current_history)}")
            return
            
        try:
            self.table.put_item(
                Item={
                    "session_id": session_id,
                    "updated_at": datetime.utcnow().isoformat() + "Z",
                    "history": current_history
                }
            )
            logger.info(f"Successfully saved session '{session_id}' to DynamoDB table '{self.table_name}'.")
        except ClientError as e:
            logger.warning(f"DynamoDB PutItem Error [{e.response['Error']['Code']}]: {e.response['Error']['Message']}. Saved to local fallback.")
            self.local_memory_store[session_id] = current_history

if __name__ == "__main__":
    memory = DynamoDBSessionMemory()
    sid = "user-session-101"
    
    # Turn 1
    memory.add_turn(sid, "What is our vacation policy?", "Full-time employees receive 20 days paid vacation per year.")
    
    # Turn 2
    memory.add_turn(sid, "What about contractors?", "Contractors are not eligible for paid vacation days.")
    
    history = memory.get_history(sid)
    print(f"--- DynamoDB Session History for '{sid}' ---")
    print(json.dumps(history, indent=2))
