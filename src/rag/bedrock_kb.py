import os
import sys
import json
import boto3
from botocore.exceptions import ClientError
from typing import Dict, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.logger import get_logger

logger = get_logger("bedrock_kb")

class BedrockKnowledgeBase:
    """
    AWS-Managed RAG Wrapper using Amazon Bedrock Knowledge Bases (bedrock-agent-runtime).
    """
    def __init__(
        self,
        knowledge_base_id: str = "KB1234567890EXAMPLE",
        region_name: str = "us-east-1",
        model_arn: str = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
    ):
        self.knowledge_base_id = os.getenv("BEDROCK_KB_ID", knowledge_base_id)
        self.region_name = region_name
        self.model_arn = model_arn
        
        try:
            self.client = boto3.client("bedrock-agent-runtime", region_name=self.region_name)
            self.mock_mode = False
        except Exception as e:
            logger.warning(f"Could not initialize bedrock-agent-runtime client ({e}). Running in simulation mode.")
            self.client = None
            self.mock_mode = True

    def retrieve(self, query: str, top_k: int = 3) -> Dict:
        """
        Calls AWS Bedrock KB `retrieve` API to get raw matching vector chunks from S3.
        """
        if self.mock_mode or not self.client:
            return self._mock_retrieve(query)
            
        try:
            response = self.client.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": top_k
                    }
                }
            )
            
            results = response.get("retrievalResults", [])
            extracted_chunks = [r["content"]["text"] for r in results]
            sources = [r["location"]["s3Location"]["uri"] for r in results if "location" in r]
            
            return {
                "status": "success",
                "query": query,
                "retrieved_chunks": extracted_chunks,
                "sources": sources
            }
        except ClientError as e:
            logger.error(f"Bedrock KB Retrieve Error [{e.response['Error']['Code']}]: {e}")
            return self._mock_retrieve(query)

    def retrieve_and_generate(self, query: str) -> Dict:
        """
        Calls AWS Bedrock KB `retrieve_and_generate` API (One-shot Managed RAG).
        """
        if self.mock_mode or not self.client:
            return self._mock_retrieve_and_generate(query)
            
        try:
            response = self.client.retrieve_and_generate(
                input={"text": query},
                retrieveAndGenerateConfiguration={
                    "type": "KNOWLEDGE_BASE",
                    "knowledgeBaseConfiguration": {
                        "knowledgeBaseId": self.knowledge_base_id,
                        "modelArn": self.model_arn
                    }
                }
            )
            
            output_text = response["output"]["text"]
            citations = response.get("citations", [])
            
            return {
                "status": "success",
                "query": query,
                "answer": output_text,
                "citations_count": len(citations),
                "is_managed_rag": True
            }
        except ClientError as e:
            logger.error(f"Bedrock KB RetrieveAndGenerate Error [{e.response['Error']['Code']}]: {e}")
            return self._mock_retrieve_and_generate(query)

    def _mock_retrieve(self, query: str) -> Dict:
        return {
            "status": "simulated",
            "query": query,
            "retrieved_chunks": [
                "Simulated Bedrock KB Chunk 1: Full-time employees receive 20 days paid vacation per year.",
                "Simulated Bedrock KB Chunk 2: Contractors are not eligible for paid vacation days."
            ],
            "sources": ["s3://enterprise-rag-docs/sample_vacation_policy.txt"]
        }

    def _mock_retrieve_and_generate(self, query: str) -> Dict:
        return {
            "status": "simulated",
            "query": query,
            "answer": f"[Amazon Bedrock Knowledge Base Answer]: Based on S3 documents, contractors do not receive paid vacation.",
            "citations_count": 1,
            "is_managed_rag": True
        }

if __name__ == "__main__":
    kb = BedrockKnowledgeBase()
    ret_res = kb.retrieve("What is contractor vacation policy?")
    print("--- Bedrock KB Retrieve Results ---")
    print(json.dumps(ret_res, indent=2))
    
    rag_res = kb.retrieve_and_generate("What is contractor vacation policy?")
    print("\n--- Bedrock KB Retrieve & Generate Results ---")
    print(json.dumps(rag_res, indent=2))
