import logging
import json
import os
import sys
from datetime import datetime

def get_logger(name: str = "enterprise_rag"):
    """
    Creates a structured JSON logger compatible with AWS CloudWatch Logs.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        class StructuredJsonFormatter(logging.Formatter):
            def format(self, record):
                log_record = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "environment": os.getenv("APP_ENV", "development"),
                }
                if hasattr(record, "request_id"):
                    log_record["request_id"] = record.request_id
                if record.exc_info:
                    log_record["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_record)
                
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
        
    return logger

if __name__ == "__main__":
    test_logger = get_logger("cloudwatch_test")
    test_logger.info("Structured CloudWatch Log Test Successful!")
