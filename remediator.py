import boto3
import requests
import time
import logging
import os
from datetime import datetime
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

def put_custom_metric(metric_name, value, unit='Count', dimensions=None):
    """Send custom metrics to CloudWatch for monitoring"""
    try:
        # Use same credential pattern as fetch_log_groups()
        if CLOUD_ACCESS_KEY and CLOUD_SECRET_KEY:
            cloudwatch = boto3.client(
                'cloudwatch', 
                region_name=CLOUD_REGION,
                aws_access_key_id=CLOUD_ACCESS_KEY,
                aws_secret_access_key=CLOUD_SECRET_KEY
            )
        else:
            # Use IAM role (for Lambda execution)
            cloudwatch = boto3.client('cloudwatch', region_name=CLOUD_REGION)
            
        metric_data = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.utcnow()
        }
        
        if dimensions:
            metric_data['Dimensions'] = dimensions
            
        cloudwatch.put_metric_data(
            Namespace='LogRemediation',
            MetricData=[metric_data]
        )
        logger.debug(f"✅ Sent metric: {metric_name}={value}")
        
    except Exception as e:
        # Check if it's a permissions issue
        if "AccessDenied" in str(e) and "cloudwatch:PutMetricData" in str(e):
            logger.debug(f"⚠️  CloudWatch metrics disabled (no permissions): {metric_name}={value}")
        else:
            logger.error(f"❌ Failed to put metric {metric_name}: {e}")

def analyze_log_group(name: str) -> dict:
    """Get AI analysis of a log group with enhanced metrics"""
    start_time = time.time()
    
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
            duration = time.time() - start_time
            
            # Send success metrics
            put_custom_metric('OpenAI_API_Success', 1)
            put_custom_metric('OpenAI_API_Duration', duration * 1000, 'Milliseconds')
            
            logger.info("Successfully got analysis from OpenAI")
            return {
                'success': True,
                'analysis': result,
                'duration': duration,
                'attempts': attempt + 1
            }

        except RateLimitError as e:
            error_msg = str(e).lower()
            put_custom_metric('OpenAI_API_RateLimit', 1)
            
            # Check for quota/billing issues
            if any(keyword in error_msg for keyword in ['quota', 'billing', 'insufficient', 'exceeded your current']):
                alert = f"🚨 *OpenAI API Quota Issue* 🚨\n\nStopped processing log group: `{name}`\nError: {str(e)}"
                post_to_slack(alert)
                put_custom_metric('OpenAI_API_QuotaExceeded', 1)
                logger.error(f"OpenAI quota exceeded: {e}")
                return {
                    'success': False,
                    'error': 'quota_exceeded',
                    'attempts': attempt + 1
                }

            # Regular rate limiting - exponential backoff
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}), retrying in {delay}s...")
                time.sleep(delay)
            else:
                put_custom_metric('OpenAI_API_Failed', 1)
                logger.error("Max retries exceeded for rate limiting")
                return {
                    'success': False,
                    'error': 'max_retries_exceeded',
                    'attempts': attempt + 1
                }

        except Exception as e:
            put_custom_metric('OpenAI_API_Error', 1)
            logger.error(f"Unexpected error analyzing log group {name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'attempts': attempt + 1
            }

    return {
        'success': False,
        'error': 'failed_after_retries',
        'attempts': max_retries
    }

def post_to_slack(text: str):
    """Post message to Slack via webhook with metrics"""
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10)
        response.raise_for_status()
        put_custom_metric('Slack_Message_Success', 1)
        logger.info("Successfully posted to Slack")
        return True
    except requests.RequestException as e:
        put_custom_metric('Slack_Message_Failed', 1)
        logger.error(f"Failed to post to Slack: {e}")
        return False

def fetch_log_groups():
    """Fetch CloudWatch log groups from AWS with metrics"""
    try:
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
            
        resp = aws_client.describe_log_groups(limit=50)  # Limit to avoid too many results
        log_groups = resp.get("logGroups", [])
        
        put_custom_metric('LogGroups_Found', len(log_groups))
        return log_groups
        
    except Exception as e:
        put_custom_metric('AWS_API_Error', 1)
        logger.error(f"Failed to fetch log groups: {e}")
        return []

def process_log_groups(limit=3):
    """Process multiple log groups with comprehensive monitoring"""
    start_time = time.time()
    
    try:
        put_custom_metric('Processing_Started', 1)
        
        groups = fetch_log_groups()
        if not groups:
            message = "🔍 No CloudWatch log groups found in the region."
            logger.info(message)
            post_to_slack(message)
            put_custom_metric('Processing_Completed', 0)
            return

        total_groups = len(groups)
        processing_count = min(limit, total_groups)
        
        logger.info(f"Found {total_groups} log groups, processing first {processing_count}")
        put_custom_metric('LogGroups_ToProcess', processing_count)
        
        successful_analyses = 0
        failed_analyses = 0
        
        # Process up to 'limit' groups
        for i, group in enumerate(groups[:limit]):
            log_group_name = group["logGroupName"]
            creation_time = group.get("creationTime", "Unknown")
            
            logger.info(f"Processing log group {i+1}/{processing_count}: {log_group_name}")
            
            # Analyze log group
            result = analyze_log_group(log_group_name)
            
            if result['success']:
                successful_analyses += 1
                
                # Format message for Slack
                slack_msg = f"""📊 *Log Group Analysis #{i+1}*

*Log Group:* `{log_group_name}`
*Created:* {time.strftime('%Y-%m-%d', time.localtime(creation_time/1000)) if isinstance(creation_time, int) else creation_time}
*Analysis Time:* {result['duration']:.2f}s (attempts: {result['attempts']})

*🤖 AI Analysis:*
{result['analysis']}

---"""
                
                post_to_slack(slack_msg)
                logger.info(f"Successfully processed: {log_group_name}")
                
            else:
                failed_analyses += 1
                error_msg = f"❌ Failed to process log group `{log_group_name}`: {result.get('error', 'Unknown error')}"
                logger.error(error_msg)
                post_to_slack(error_msg)
            
            # Small delay between processing
            time.sleep(2)
        
        # Send metrics
        put_custom_metric('LogGroups_Processed_Success', successful_analyses)
        put_custom_metric('LogGroups_Processed_Failed', failed_analyses)
        
        # Summary message
        total_duration = time.time() - start_time
        summary = f"""✅ *Processing Complete!* 

📈 **Summary:**
- Analyzed: {successful_analyses}/{processing_count} log groups
- Failed: {failed_analyses}
- Total time: {total_duration:.2f}s
- Total log groups available: {total_groups}"""

        post_to_slack(summary)
        put_custom_metric('Processing_Duration', total_duration, 'Seconds')
        put_custom_metric('Processing_Completed', 1)
        logger.info("Log group processing completed successfully")
        
    except Exception as e:
        error_msg = f"🚨 *Critical Error* in log processing: {str(e)}"
        logger.error(error_msg)
        post_to_slack(error_msg)
        put_custom_metric('Processing_Critical_Error', 1)

if __name__ == "__main__":
    logger.info("🚀 Starting AI-Driven Log Remediation Tool")
    
    # Send startup notification
    startup_msg = "🤖 *AI Log Remediation Started* \nBeginning analysis of CloudWatch log groups..."
    post_to_slack(startup_msg)
    
    # Process log groups (limit to 3 to avoid spam and costs)
    process_log_groups(limit=3)