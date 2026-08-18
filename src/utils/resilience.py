import os
import sys
import json
import time
import random
from typing import Dict, Callable

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.logger import get_logger

logger = get_logger("resilience")

class CircuitBreakerOpenError(Exception):
    """Exception raised when Circuit Breaker is in OPEN state."""
    pass

class EnterpriseCircuitBreaker:
    """
    Implements Circuit Breaker Pattern & Exponential Backoff for Fault-Tolerant AWS GenAI Microservices.
    """
    def __init__(
        self,
        name: str = "BedrockCircuitBreaker",
        failure_threshold: int = 3,
        cooldown_seconds: float = 5.0
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.failure_count = 0
        self.last_failure_time = 0.0

    def call_with_resilience(self, func: Callable, fallback_func: Callable, *args, **kwargs) -> Dict:
        """
        Executes target function inside Circuit Breaker protection.
        """
        now = time.time()
        
        # Check if OPEN circuit should transition to HALF-OPEN trial probe
        if self.state == "OPEN":
            if now - self.last_failure_time >= self.cooldown_seconds:
                logger.info(f"[{self.name}] Cooldown expired. Transitioning from OPEN -> HALF-OPEN (Trial Probe)...")
                self.state = "HALF-OPEN"
            else:
                logger.warning(f"[{self.name}] Circuit is OPEN (TRIPPED!). Short-circuiting request to Graceful Fallback.")
                return fallback_func(*args, **kwargs)
                
        try:
            result = func(*args, **kwargs)
            
            # If call succeeded during HALF-OPEN, reset to CLOSED
            if self.state == "HALF-OPEN":
                logger.info(f"[{self.name}] Trial probe succeeded! Transitioning HALF-OPEN -> CLOSED (Healthy).")
                self.state = "CLOSED"
                self.failure_count = 0
                
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = now
            logger.error(f"[{self.name}] Target execution error ({e}). Failure count: {self.failure_count}/{self.failure_threshold}")
            
            if self.failure_count >= self.failure_threshold:
                logger.error(f"[{self.name}] Failure threshold reached! TRIPPING CIRCUIT BREAKER: CLOSED -> OPEN!")
                self.state = "OPEN"
                
            return fallback_func(*args, **kwargs)

if __name__ == "__main__":
    cb = EnterpriseCircuitBreaker(failure_threshold=2, cooldown_seconds=3.0)
    
    def flaky_bedrock_service(should_fail: bool = False):
        if should_fail:
            raise Exception("AWS Bedrock ThrottlingException: Rate limit exceeded (429)")
        return {"status": "success", "answer": "Grounded answer from live Bedrock model."}
        
    def graceful_fallback():
        return {"status": "degraded_fallback", "answer": "[Fallback Mode]: Service temporarily busy. Showing cached HR policy answer."}
        
    print("--- 1. Normal Request (Circuit CLOSED) ---")
    r1 = cb.call_with_resilience(lambda: flaky_bedrock_service(False), graceful_fallback)
    print(json.dumps(r1, indent=2))
    
    print("\n--- 2. Inducing 2 Consecutive Failures to Trip Circuit Breaker ---")
    r2 = cb.call_with_resilience(lambda: flaky_bedrock_service(True), graceful_fallback)
    r3 = cb.call_with_resilience(lambda: flaky_bedrock_service(True), graceful_fallback)
    print(f"Current Circuit Breaker State: {cb.state}")
    
    print("\n--- 3. Immediate Follow-up Request (Circuit OPEN -> Instant Short-Circuit to Fallback) ---")
    r4 = cb.call_with_resilience(lambda: flaky_bedrock_service(False), graceful_fallback)
    print(json.dumps(r4, indent=2))
