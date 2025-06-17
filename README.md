# AI-Driven Log Remediation Tool

A learning project that connects AWS CloudWatch logs with OpenAI to get plain English explanations, then posts them to Slack.

## Quick Start

```bash
git clone https://github.com/houman30/ai-remediator.git
cd ai-remediator
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp config.py.template config.py
# Edit config.py with your API keys
python remediator.py
```

## What You Need

- Python 3.8+
- AWS account with CloudWatch access
- OpenAI API key 
- Slack webhook URL

## What It Does

1. Fetches your AWS CloudWatch log groups
2. Sends log group names to OpenAI for analysis
3. Posts AI explanations to your Slack channel
4. Handles rate limits and errors automatically

## Configuration

Edit `config.py` with:
- `CLOUD_REGION` - AWS region
- `CLOUD_ACCESS_KEY` - AWS access key
- `CLOUD_SECRET_KEY` - AWS secret key
- `OPENAI_API_KEY` - OpenAI API key
- `SLACK_WEBHOOK_URL` - Slack webhook URL

## Notes

Built this to learn API integrations. It processes the first 3 log groups by default (changeable in the code). Has retry logic for rate limits and posts errors to Slack.

Don't commit your `config.py` - it's gitignored for security.