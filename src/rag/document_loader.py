import os
import boto3
from botocore.exceptions import ClientError

def load_local_document(file_path: str) -> str:
    """Reads content from a local text document."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Document not found at: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def simulate_s3_upload(bucket_name: str, object_key: str, file_path: str):
    """
    Demonstrates how boto3 uploads an enterprise document to AWS S3.
    Note: Requires active AWS credentials and a valid bucket.
    """
    s3_client = boto3.client("s3")
    try:
        print(f"Uploading {file_path} to s3://{bucket_name}/{object_key}...")
        s3_client.upload_file(file_path, bucket_name, object_key)
        print("Upload successful!")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        print(f"S3 Upload Error [{error_code}]: {e}")
        raise e

if __name__ == "__main__":
    sample_path = os.path.join("docs", "sample_vacation_policy.txt")
    content = load_local_document(sample_path)
    print("--- Loaded Document Preview ---")
    print(content[:250])
    print("-------------------------------")
