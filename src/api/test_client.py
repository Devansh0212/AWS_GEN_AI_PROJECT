import urllib.request
import json
import sys

def test_api_gateway(question: str, session_id: str = "demo-session-101", url: str = "http://localhost:8080/ask"):
    """
    Sends an HTTP POST request to the API Gateway endpoint with session_id memory tracking.
    """
    payload_dict = {"question": question, "session_id": session_id}
    payload = json.dumps(payload_dict).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    
    print(f"Sending HTTP POST to {url} [session_id: {session_id}]...")
    print(f"Request Payload: {json.dumps(payload_dict)}")
    
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            response_body = response.read().decode("utf-8")
            print(f"\nReceived HTTP Response [{status_code}]:")
            parsed = json.loads(response_body)
            print(json.dumps(parsed, indent=2))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error [{e.code}]: {e.read().decode('utf-8')}")
    except urllib.error.URLError as e:
        print(f"Connection Error: {e.reason}")
        print("Make sure the API Gateway server is running via: uv run python src/api/api_server.py")

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "What is our vacation policy?"
    sid = sys.argv[2] if len(sys.argv) > 2 else "demo-session-101"
    test_api_gateway(q, session_id=sid)
