import json
import os
from typing import List, Dict

def analyze_logs(log_lines: List[str]) -> Dict:
    """
    Simulates AWS CloudWatch Log Insights parsing and metric extraction.
    """
    total_logs = 0
    error_logs = []
    info_logs = 0
    warning_logs = 0
    
    for line in log_lines:
        line = line.strip()
        if not line:
            continue
        total_logs += 1
        try:
            log_entry = json.loads(line)
            level = log_entry.get("level", "INFO").upper()
            if level == "ERROR":
                error_logs.append(log_entry)
            elif level == "WARNING":
                warning_logs.append(log_entry)
            else:
                info_logs += 1
        except json.JSONDecodeError:
            # Unstructured plain text log line
            if "ERROR" in line or "Exception" in line:
                error_logs.append({"raw_message": line, "level": "ERROR"})
            else:
                info_logs += 1

    error_rate = (len(error_logs) / total_logs * 100) if total_logs > 0 else 0.0
    
    return {
        "total_log_events": total_logs,
        "info_count": info_logs,
        "error_count": len(error_logs),
        "error_rate_percentage": round(error_rate, 2),
        "errors_extracted": error_logs
    }

if __name__ == "__main__":
    sample_cloudwatch_stream = [
        json.dumps({"timestamp": "2026-08-12T11:45:00Z", "level": "INFO", "message": "Lambda started, request_id=req-101"}),
        json.dumps({"timestamp": "2026-08-12T11:45:01Z", "level": "INFO", "message": "Fetched document from s3://enterprise-rag-docs/policy.txt"}),
        json.dumps({"timestamp": "2026-08-12T11:45:02Z", "level": "ERROR", "message": "Bedrock invocation failed: AccessDeniedException", "request_id": "req-101"}),
    ]
    
    results = analyze_logs(sample_cloudwatch_stream)
    print("--- CloudWatch Log Insights Query Results ---")
    print(json.dumps(results, indent=2))
