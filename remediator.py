import boto3
import openai
import requests
from config import SLACK_WEBHOOK_URL
from config import CLOUD_REGION, CLOUD_ACCESS_KEY, CLOUD_SECRET_KEY, OPENAI_API_KEY

#Configure the OPENAI client
openai.api_key = OPENAI_API_KEY
def fetch_log_groups():
    client = boto3.client(
        "logs",
        region_name=CLOUD_REGION,
        aws_access_key_id=CLOUD_ACCESS_KEY,
        aws_secret_access_key=CLOUD_SECRET_KEY
    )
    response = client.describe_log_groups()
    return response.get("logGroups", [])


def analyze_log_group(name: str) -> str:
    prompt = f"Here is an AWS log group name:\n{name}\n\nExplain in 2–3 sentences…"
    for attempt in range(5):
        try:
            resp = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            return resp.choices[0].message.content.strip()
        except RateLimitError:
            wait = (2 ** attempt)  # 1s, 2s, 4s, 8s, 16s
            print(f"Rate limit hit, retrying in {wait} seconds…")
            time.sleep(wait)
    raise Exception("Failed after multiple rate‐limit retries.")


def post_to_slack(message: str):
    """
    Sends a simple text message to the Slack channel configured in SLACK_WEBHOOK_URL.
    """
    payload = {"text": message}
    try:
        res = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        res.raise_for_status()
    except requests.RequestException as e:
        # If Slack fails, print to stderr or log it, but don't crash the whole script
        print(f"Failed to send Slack notification: {e}")



if __name__ == "__main__":
    groups = fetch_log_groups()
    if not groups:
        notice = "No CloudWatch log groups found."
        print(notice)
        post_to_slack(notice)
    else:
        first_name = groups[0]["logGroupName"]
        notice = f"🔍 Analyzing log group: *{first_name}*"
        print(notice)
        post_to_slack(notice)

        explanation = analyze_log_group(first_name)
        print("LLM suggests:", explanation)

        # Format Slack message: bullet list or code block
        slack_message = (
            f"*Log Group:* `{first_name}`\n"
            f"*LLM Explanation:*\n```{explanation}```"
        )
        post_to_slack(slack_message)


