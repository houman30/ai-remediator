import boto3
import openai
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
    """
    Ask the LLM to explain what this log group likely contains.
    We’re now using the `gpt-4.1-mini` model in the v1 API.
    """
    prompt = (
        "Here is an AWS CloudWatch log group name:\n"
        f"{name}\n\n"
        "In 2–3 sentences, explain what kinds of events or logs this group probably holds."
    )

    # Use the new v1/chat/completions client
    resp = openai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
    )
    return resp.choices[0].message.content.strip()






if __name__ == "__main__":
    groups = fetch_log_groups()
    if not groups:
        print("No log groups found.")
    else:
        first_name = groups[0]["logGroupName"]
        print("Analyzing log group:", first_name)
        explanation = analyze_log_group(first_name)
        print("LLM suggests:", explanation)

