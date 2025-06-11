import boto3
import requests

from config import (
    CLOUD_REGION,
    CLOUD_ACCESS_KEY,
    CLOUD_SECRET_KEY,
    SLACK_WEBHOOK_URL,
)


def post_to_slack(text: str):
    """Post message to Slack via webhook"""
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10)
        response.raise_for_status()
        print("✅ Posted to Slack successfully")
        return True
    except requests.RequestException as e:
        print(f"❌ Failed to post to Slack: {e}")
        return False


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
    
    # Send startup notification to Slack
    post_to_slack("🤖 AI Log Remediation Started - Checking CloudWatch log groups...")
    
    groups = fetch_log_groups()
    print(f"Found {len(groups)} log groups")
    
    if groups:
        message = f"📊 Found {len(groups)} CloudWatch log groups:\n"
        for i, group in enumerate(groups[:3]):  # Show first 3
            log_name = group['logGroupName']
            print(f"{i+1}. {log_name}")
            message += f"• {log_name}\n"
        
        post_to_slack(message)
    else:
        no_groups_msg = "🔍 No CloudWatch log groups found in the region."
        print(no_groups_msg)
        post_to_slack(no_groups_msg)