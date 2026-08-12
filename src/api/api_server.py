import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
import os

# Add src to path so we can import rag_handler
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.handlers.rag_handler import lambda_handler

class APIGatewaySimulatorHandler(BaseHTTPRequestHandler):
    """
    Simulates AWS API Gateway (HTTP API v2.0) forwarding requests to AWS Lambda.
    """
    def do_POST(self):
        if self.path == "/ask":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            
            # Construct API Gateway v2.0 Event Payload
            api_gateway_event = {
                "version": "2.0",
                "routeKey": "POST /ask",
                "rawPath": "/ask",
                "headers": dict(self.headers),
                "body": post_data,
                "isBase64Encoded": False,
                "requestContext": {
                    "http": {
                        "method": "POST",
                        "path": "/ask",
                        "protocol": "HTTP/1.1",
                        "sourceIp": self.client_address[0]
                    }
                }
            }
            
            print(f"\n[API Gateway Simulator] Forwarding POST /ask to Lambda...")
            # Invoke Lambda handler
            response = lambda_handler(api_gateway_event, None)
            
            # Send HTTP Response back to client
            status_code = response.get("statusCode", 200)
            self.send_response(status_code)
            
            for key, val in response.get("headers", {}).items():
                self.send_header(key, val)
            self.end_headers()
            
            self.wfile.write(response.get("body", "").encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Route '{self.path}' not found"}).encode("utf-8"))

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "service": "API Gateway Simulator"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def run_server(port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, APIGatewaySimulatorHandler)
    print(f"🚀 API Gateway Simulator running on http://localhost:{port}")
    print(f"   Available Routes:")
    print(f"   - GET  http://localhost:{port}/health")
    print(f"   - POST http://localhost:{port}/ask")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping API Gateway Simulator server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
