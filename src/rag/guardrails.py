import re
import os
import sys
from typing import Dict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.logger import get_logger

logger = get_logger("guardrails")

class BedrockGuardrailValidator:
    """
    Implements Input & Output Safety Guardrails (Prompt Injection, Denied Topics, PII Redaction).
    """
    DENIED_TOPICS = [
        "bypass security",
        "hack system",
        "ignore instructions",
        "investment advice",
        "political endorsement"
    ]
    
    PII_PATTERNS = {
        "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
        "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b",
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    }

    def validate_input(self, prompt: str) -> Dict:
        """
        Input Guardrail (Before Hook): Checks for prompt injection and denied topics.
        """
        prompt_lower = prompt.lower()
        
        for topic in self.DENIED_TOPICS:
            if topic in prompt_lower:
                logger.warning(f"Guardrail Blocked Input: Denied topic '{topic}' detected in prompt.")
                return {
                    "is_allowed": False,
                    "reason": f"Guardrail Rejection: Query contains prohibited topic ('{topic}').",
                    "action": "BLOCKED_INPUT"
                }
                
        return {"is_allowed": True, "reason": "Input passed guardrail checks."}

    def sanitize_output(self, text: str) -> Dict:
        """
        Output Guardrail (After Hook): Redacts sensitive PII from LLM generated response.
        """
        sanitized_text = text
        redactions_found = []
        
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, sanitized_text)
            if matches:
                redactions_found.append(f"{pii_type} ({len(matches)} instance(s))")
                sanitized_text = re.sub(pattern, f"[{pii_type}_REDACTED]", sanitized_text)
                
        if redactions_found:
            logger.info(f"Guardrail Output Sanitized: Redacted {', '.join(redactions_found)}.")
            
        return {
            "sanitized_text": sanitized_text,
            "has_redactions": len(redactions_found) > 0,
            "redactions": redactions_found
        }

if __name__ == "__main__":
    validator = BedrockGuardrailValidator()
    
    # Test 1: Denied Topic Input
    bad_input = "Can you help me bypass security on our servers?"
    res1 = validator.validate_input(bad_input)
    print("--- Test 1: Denied Topic Input Check ---")
    print(res1)
    
    # Test 2: PII Redaction Output
    output_with_pii = "Employee John Doe SSN is 123-45-6789 and email is john@company.com."
    res2 = validator.sanitize_output(output_with_pii)
    print("\n--- Test 2: PII Redaction Check ---")
    print(res2)
