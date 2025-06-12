import boto3
import requests
import time
from openai import OpenAI, RateLimitError

from config import (
    CLOUD_REGION,
    CLOUD_ACCESS_KEY,
    CLOUD_SECRET_KEY,
    OPENAI_API_KEY,
    SLACK_WEBHOOK_URL,
)

# Configure the OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def analyze_log_group(name: str) -> str:
    """Get AI analysis of a log group with retry logic"""
    prompt = f"""Analyze this AWS CloudWatch log group: {name}

Please provide a brief analysis covering:
1. What type of AWS service this likely belongs to
2. What kind of logs it probably contains
3. Any potential issues or patterns to monitor

Keep it concise (2-3 sentences)."""
    
    max_retries = 4
    base_delay = 1

    for attempt in range(max_retries):
        try:
            print(f"🤖 Getting AI analysis for: {name} (attempt {attempt + 1})")
            resp = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            result = resp.choices[0].message.content.strip()
            print("✅ AI analysis complete")
            return result

        except RateLimitError as e:
            error_msg = str(e).lower()
            
            # Check for quota/billing issues
            if any(keyword in error_msg for keyword in ['quota', 'billing', 'insufficient', 'exceeded your current']):
                alert = f"🚨 *OpenAI API Quota Issue* 🚨\n\nStopped processing log group: `{name}`\nError: {str(e)}"
                post_to_slack(alert)
                print(f"❌ OpenAI quota exceeded: {e}")
                raise RuntimeError(f"OpenAI quota exceeded: {e}")

            # Regular rate limiting - exponential backoff
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"⏳ Rate limited (attempt {attempt + 1}/{max_retries}), retrying in {delay}s...")
                time.sleep(delay)
            else:
                print("❌ Max retries exceeded for rate limiting")
                raise RuntimeError("Max retries exceeded for rate limiting")

        except Exception as e:
            error_msg = f"❌ Error getting AI analysis: {str(e)[:100]}..."
            print(error_msg)
            return error_msg

    return "Failed to analyze after multiple attempts"


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
    post_to_slack("🤖 AI Log Remediation Started - Analyzing CloudWatch log groups...")
    
    groups = fetch_log_groups()
    print(f"Found {len(groups)} log groups")
    
    if groups:
        # Analyze the first log group
        first_group = groups[0]
        log_name = first_group['logGroupName']
        
        print(f"Analyzing: {log_name}")
        analysis = analyze_log_group(log_name)
        
        # Send analysis to Slack
        slack_msg = f"""📊 *Log Group Analysis*

*Log Group:* `{log_name}`

*🤖 AI Analysis:*
{analysis}
"""
        post_to_slack(slack_msg)
        print("✅ Analysis complete!")
        
    else:
        no_groups_msg = "🔍 No CloudWatch log groups found in the region."
        print(no_groups_msg)
        post_to_slack(no_groups_msg)