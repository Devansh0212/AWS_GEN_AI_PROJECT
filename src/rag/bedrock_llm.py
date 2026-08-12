import json
import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict

class BedrockLLM:
    """
    Production-ready wrapper for Amazon Bedrock Foundation Models using the unified Converse API.
    """
    def __init__(
        self,
        model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0",
        region_name: str = "us-east-1",
        temperature: float = 0.2,
        max_tokens: int = 1000
    ):
        self.model_id = model_id
        self.region_name = region_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize boto3 bedrock-runtime client
        try:
            self.client = boto3.client("bedrock-runtime", region_name=self.region_name)
            self.mock_mode = False
        except Exception as e:
            print(f"[BedrockLLM Warning] Could not initialize boto3 Bedrock client ({e}). Falling back to local simulation mode.")
            self.client = None
            self.mock_mode = True

    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> Dict:
        """
        Invokes Amazon Bedrock using the unified Converse API.
        """
        if self.mock_mode or not self.client:
            return self._generate_mock_response(prompt, system_prompt)
            
        system_messages = [{"text": system_prompt}] if system_prompt else []
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
        
        inference_config = {
            "temperature": self.temperature,
            "maxTokens": self.max_tokens,
            "topP": 0.9
        }
        
        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=messages,
                system=system_messages,
                inferenceConfig=inference_config
            )
            
            output_text = response["output"]["message"]["content"][0]["text"]
            usage = response.get("usage", {})
            
            return {
                "status": "success",
                "model_id": self.model_id,
                "response_text": output_text,
                "usage": {
                    "input_tokens": usage.get("inputTokens", 0),
                    "output_tokens": usage.get("outputTokens", 0),
                    "total_tokens": usage.get("totalTokens", 0)
                }
            }
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_msg = e.response["Error"]["Message"]
            print(f"[Bedrock API Error] {error_code}: {error_msg}")
            
            if error_code == "AccessDeniedException":
                print("\n💡 TIP: Ensure your IAM role/user has 'bedrock:InvokeModel' permission and Model Access is enabled in AWS Console.")
            elif error_code == "ResourceNotFoundException":
                print(f"\n💡 TIP: Model ID '{self.model_id}' was not found in region '{self.region_name}'.")
                
            return {
                "status": "error",
                "error_code": error_code,
                "error_message": error_msg,
                "fallback_response": f"[Simulated Response due to {error_code}] In enterprise RAG, Bedrock provides grounded context answers."
            }

    def _generate_mock_response(self, prompt: str, system_prompt: Optional[str]) -> Dict:
        """Simulates Bedrock response when running in local offline mode."""
        return {
            "status": "simulated",
            "model_id": f"{self.model_id} (Simulated)",
            "response_text": f"Simulated Bedrock Response to query: '{prompt}'. [System Prompt: {system_prompt}]",
            "usage": {"input_tokens": 25, "output_tokens": 30, "total_tokens": 55}
        }

if __name__ == "__main__":
    llm = BedrockLLM()
    res = llm.generate_response(
        prompt="Explain the vacation policy carry-over limit in 2 sentences.",
        system_prompt="You are an helpful Enterprise HR Assistant."
    )
    print("--- Bedrock LLM Test Result ---")
    print(json.dumps(res, indent=2))
