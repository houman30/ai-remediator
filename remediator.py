import boto3

from config import (
    CLOUD_REGION,
    CLOUD_ACCESS_KEY,
    CLOUD_SECRET_KEY,
)


def fetch_log_groups():
    """Fetch CloudWatch log groups from AWS"""
    aws_client = boto3.client(
        "logs",
        region_name=CLOUD_REGION,
        aws_access_key_id=CLOUD_ACCESS_KEY,
        aws_secret_access_key=CLOUD_SECRET_KEY,
    )
    resp = aws_client.describe_log_groups()
    return resp.get("logGroups", [])


if __name__ == "__main__":
    print("🚀 Starting AI-Driven Log Remediation Tool")
    
    groups = fetch_log_groups()
    print(f"Found {len(groups)} log groups")
    
    if groups:
        for i, group in enumerate(groups[:3]):  # Show first 3
            print(f"{i+1}. {group['logGroupName']}")
    else:
        print("No log groups found")