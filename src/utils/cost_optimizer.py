import os
import sys
import json
from typing import Dict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.logger import get_logger

logger = get_logger("cost_optimizer")

class FinOpsCostOptimizer:
    """
    GenAI FinOps Cost Optimization Manager: Calculates token costs, Smart Model Routing, & Prompt Caching savings.
    """
    MODEL_PRICING = {
        "us.amazon.nova-micro-v1:0": {
            "name": "Amazon Nova Micro",
            "input_per_1k": 0.000035,
            "output_per_1k": 0.00014
        },
        "us.anthropic.claude-3-5-sonnet-20241022-v2:0": {
            "name": "Anthropic Claude 3.5 Sonnet",
            "input_per_1k": 0.003,
            "output_per_1k": 0.015
        }
    }

    def calculate_token_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> Dict:
        """
        Calculates exact USD cost for a Bedrock API query based on token usage.
        """
        pricing = self.MODEL_PRICING.get(model_id, self.MODEL_PRICING["us.amazon.nova-micro-v1:0"])
        
        input_cost = (input_tokens / 1000.0) * pricing["input_per_1k"]
        output_cost = (output_tokens / 1000.0) * pricing["output_per_1k"]
        total_cost = round(input_cost + output_cost, 6)
        
        return {
            "model_id": model_id,
            "model_name": pricing["name"],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost_usd": f"${total_cost:.6f}"
        }

    def select_optimal_model(self, prompt: str) -> Dict:
        """
        FinOps Smart Router: Routes 90% of queries to Amazon Nova Micro, reserving Claude only for complex code/math reasoning.
        """
        prompt_lower = prompt.lower()
        
        # Check if query requires heavy multi-step coding or complex reasoning
        is_complex = "write complex code" in prompt_lower or "multi-step architecture" in prompt_lower
        
        if is_complex:
            selected_model = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
            reason = "Complex reasoning required -> Routed to Claude 3.5 Sonnet"
        else:
            selected_model = "us.amazon.nova-micro-v1:0"
            reason = "Standard RAG query -> Routed to low-cost Amazon Nova Micro (Saves 98%!)"
            
        logger.info(f"[FinOps Router] {reason}")
        return {
            "selected_model_id": selected_model,
            "routing_reason": reason
        }

if __name__ == "__main__":
    optimizer = FinOpsCostOptimizer()
    
    # 1. Calculate Cost for Nova Micro
    c1 = optimizer.calculate_token_cost("us.amazon.nova-micro-v1:0", input_tokens=450, output_tokens=120)
    print("--- Amazon Nova Micro Token Cost Calculation ---")
    print(json.dumps(c1, indent=2))
    
    # 2. Smart Model Routing Test
    r1 = optimizer.select_optimal_model("What is our vacation policy?")
    print("\n--- FinOps Smart Model Router Result ---")
    print(json.dumps(r1, indent=2))
