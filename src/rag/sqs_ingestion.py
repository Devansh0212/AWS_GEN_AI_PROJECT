import os
import sys
import json
from datetime import datetime
from typing import Dict, List
import boto3
from botocore.exceptions import ClientError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.rag.document_loader import load_local_document
from src.rag.rag_engine import CustomRAGEngine
from src.utils.logger import get_logger

logger = get_logger("sqs_ingestion")

class SQSDocumentIngestionPipeline:
    """
    Decoupled Asynchronous Document Ingestion Pipeline using Amazon SQS.
    """
    def __init__(self, queue_url: str = "https://sqs.us-east-1.amazonaws.com/866865535007/EnterpriseDocIngestionQueue"):
        self.queue_url = os.getenv("SQS_QUEUE_URL", queue_url)
        self.rag_engine = CustomRAGEngine()
        
        # Local in-memory queue fallback for offline simulation
        self.local_queue: List[Dict] = []
        
        try:
            self.sqs_client = boto3.client("sqs", region_name="us-east-1")
            self.mock_mode = False
        except Exception as e:
            logger.warning(f"Could not initialize SQS boto3 client ({e}). Using local SQS queue fallback.")
            self.sqs_client = None
            self.mock_mode = True

    def publish_document_event(self, bucket_name: str, object_key: str) -> Dict:
        """
        Producer Step: Sends an S3 Document Created event message to the SQS queue.
        """
        message_payload = {
            "event_id": f"evt-{int(datetime.utcnow().timestamp())}",
            "event_type": "s3:ObjectCreated:Put",
            "bucket_name": bucket_name,
            "object_key": object_key,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        logger.info(f"[SQS Producer] Publishing document event for 's3://{bucket_name}/{object_key}' to SQS...")
        
        if self.mock_mode or not self.sqs_client:
            self.local_queue.append(message_payload)
            return {"status": "queued_local", "message_id": message_payload["event_id"], "queue_size": len(self.local_queue)}
            
        try:
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_payload)
            )
            return {"status": "queued_sqs", "message_id": response.get("MessageId")}
        except ClientError as e:
            logger.warning(f"SQS SendMessage Error [{e.response['Error']['Code']}]: Using local queue fallback.")
            self.local_queue.append(message_payload)
            return {"status": "queued_local", "message_id": message_payload["event_id"], "queue_size": len(self.local_queue)}

    def process_worker_batch(self) -> Dict:
        """
        Consumer Step (Lambda Worker): Polls SQS queue, processes document chunks into vector index, and deletes message.
        """
        logger.info("[SQS Consumer Worker] Polling SQS queue for document ingestion tasks...")
        
        messages_to_process = []
        if self.mock_mode or not self.sqs_client or len(self.local_queue) > 0:
            messages_to_process = list(self.local_queue)
            self.local_queue.clear()
        else:
            try:
                res = self.sqs_client.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=5,
                    WaitTimeSeconds=2
                )
                for msg in res.get("Messages", []):
                    messages_to_process.append(json.loads(msg["Body"]))
                    # Delete processed message from SQS
                    self.sqs_client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=msg["ReceiptHandle"])
            except ClientError as e:
                logger.warning(f"SQS ReceiveMessage Error: {e}")
                
        processed_count = 0
        for item in messages_to_process:
            logger.info(f"[SQS Worker Processing] Ingesting document: {item['object_key']} from bucket '{item['bucket_name']}'...")
            
            # Simulated text ingestion into vector index
            sample_doc = os.path.join("docs", "sample_vacation_policy.txt")
            if os.path.exists(sample_doc):
                content = load_local_document(sample_doc)
                self.rag_engine.index.add_document(content, doc_name=item["object_key"])
                processed_count += 1
                
        return {
            "status": "batch_completed",
            "documents_processed": processed_count,
            "vector_index_total_chunks": len(self.rag_engine.index.chunks)
        }

if __name__ == "__main__":
    pipeline = SQSDocumentIngestionPipeline()
    
    # 1. Producer: Publish 2 document upload events to SQS
    p1 = pipeline.publish_document_event("enterprise-rag-docs-866865535007", "policies/2026_hr_handbook.pdf")
    p2 = pipeline.publish_document_event("enterprise-rag-docs-866865535007", "policies/security_compliance.pdf")
    print("--- SQS Producer Results ---")
    print(json.dumps(p1, indent=2))
    print(json.dumps(p2, indent=2))
    
    # 2. Consumer Worker: Process batch from SQS Queue into Vector Index
    worker_res = pipeline.process_worker_batch()
    print("\n--- SQS Worker Consumer Batch Execution ---")
    print(json.dumps(worker_res, indent=2))
