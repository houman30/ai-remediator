import boto3
import requests
import time
import logging
import os
from openai import OpenAI, RateLimitError

# Use environment variables for Lambda compatibility
CLOUD_REGION = os.getenv('CLOUD_REGION', 'us-east-1')
CLOUD_ACCESS_KEY = os.getenv('CLOUD_ACCESS_KEY')
CLOUD_SECRET_KEY = os.getenv('CLOUD_SECRET_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Fallback to config.py for local development
if not CLOUD_ACCESS_KEY:
    try:
        from config import (
            CLOUD_REGION as CONFIG_REGION,
            CLOUD_ACCESS_KEY as CONFIG_ACCESS_KEY,
            CLOUD_SECRET_KEY as CONFIG_SECRET_KEY,
            OPENAI_API_KEY as CONFIG_OPENAI_KEY,
            SLACK_WEBHOOK_URL as CONFIG_SLACK_URL,
        )
        CLOUD_REGION = CONFIG_REGION
        CLOUD_ACCESS_KEY = CONFIG_ACCESS_KEY
        CLOUD_SECRET_KEY = CONFIG_SECRET_KEY
        OPENAI_API_KEY = CONFIG_OPENAI_KEY
        SLACK_WEBHOOK_URL = CONFIG_SLACK_URL
        logger.info("Using config.py for credentials")
    except ImportError:
        logger.error("No config.py found and environment variables not set")

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
            logger.info(f"Calling OpenAI API for log group: {name} (attempt {attempt + 1})")
            resp = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            result = resp.choices[0].message.content.strip()
            logger.info("Successfully got analysis from OpenAI")
            return result

        except RateLimitError as e:
            error_msg = str(e).lower()
            
            # Check for quota/billing issues
            if any(keyword in error_msg for keyword in ['quota', 'billing', 'insufficient', 'exceeded your current']):
                alert = f"🚨 *OpenAI API Quota Issue* 🚨\n\nStopped processing log group: `{name}`\nError: {str(e)}"
                post_to_slack(alert)
                logger.error(f"OpenAI quota exceeded: {e}")
                raise RuntimeError(f"OpenAI quota exceeded: {e}")

            # Regular rate limiting - exponential backoff
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}), retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error("Max retries exceeded for rate limiting")
                raise RuntimeError("Max retries exceeded for rate limiting")

        except Exception as e:
            logger.error(f"Unexpected error analyzing log group {name}: {e}")
            return f"❌ Error analyzing log group: {str(e)[:100]}..."

    return "Failed to analyze after multiple attempts"

def post_to_slack(text: str):
    """Post message to Slack via webhook"""
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10)
        response.raise_for_status()
        logger.info("Successfully posted to Slack")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to post to Slack: {e}")
        return False

def fetch_log_groups():
    """Fetch CloudWatch log groups from AWS"""
    # Use IAM role if running in Lambda, otherwise use provided credentials
    if CLOUD_ACCESS_KEY and CLOUD_SECRET_KEY:
        aws_client = boto3.client(
            "logs",
            region_name=CLOUD_REGION,
            aws_access_key_id=CLOUD_ACCESS_KEY,
            aws_secret_access_key=CLOUD_SECRET_KEY,
        )
    else:
        # Use IAM role (for Lambda execution)
        aws_client = boto3.client("logs", region_name=CLOUD_REGION)
        
    resp = aws_client.describe_log_groups()
    return resp.get("logGroups", [])

def process_log_groups(limit=3):
    """Process multiple log groups up to the specified limit"""
    try:
        groups = fetch_log_groups()
        if not groups:
            message = "🔍 No CloudWatch log groups found in the region."
            logger.info(message)
            post_to_slack(message)
            return

        total_groups = len(groups)
        logger.info(f"Found {total_groups} log groups, processing first {min(limit, total_groups)}")
        
        # Process up to 'limit' groups
        for i, group in enumerate(groups[:limit]):
            log_group_name = group["logGroupName"]
            creation_time = group.get("creationTime", "Unknown")
            
            logger.info(f"Processing log group {i+1}/{min(limit, total_groups)}: {log_group_name}")
            
            try:
                explanation = analyze_log_group(log_group_name)
                
                # Format message for Slack
                slack_msg = f"""📊 *Log Group Analysis #{i+1}*

*Log Group:* `{log_group_name}`
*Created:* {time.strftime('%Y-%m-%d', time.localtime(creation_time/1000)) if isinstance(creation_time, int) else creation_time}

*🤖 AI Analysis:*
{explanation}

---"""
                
                post_to_slack(slack_msg)
                logger.info(f"Successfully processed: {log_group_name}")
                
                # Small delay between processing to be nice to APIs
                time.sleep(2)
                
            except Exception as e:
                error_msg = f"❌ Failed to process log group `{log_group_name}`: {str(e)}"
                logger.error(error_msg)
                post_to_slack(error_msg)
                continue
        
        # Summary message
        summary = f"✅ *Processing Complete!* \nAnalyzed {min(limit, total_groups)} of {total_groups} log groups."
        post_to_slack(summary)
        logger.info("Log group processing completed successfully")
        
    except Exception as e:
        error_msg = f"🚨 *Critical Error* in log processing: {str(e)}"
        logger.error(error_msg)
        post_to_slack(error_msg)

if __name__ == "__main__":
    logger.info("🚀 Starting AI-Driven Log Remediation Tool")
    
    # Send startup notification
    startup_msg = "🤖 *AI Log Remediation Started* \nBeginning analysis of CloudWatch log groups..."
    post_to_slack(startup_msg)
    
    # Process log groups (limit to 3 to avoid spam and costs)
    process_log_groups(limit=3)