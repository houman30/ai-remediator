# AI Log Remediation Tool

A Python application that analyzes AWS CloudWatch log groups using OpenAI and sends insights via Slack.

## What It Does

1. Fetches CloudWatch log groups from your AWS account
2. Analyzes each log group using OpenAI GPT-3.5
3. Sends analysis results to Slack with timing information
4. Handles API rate limits and errors gracefully

## Tech Stack

- **Python 3.10** - Main application runtime
- **OpenAI API** - GPT-3.5 for log analysis
- **AWS SDK (boto3)** - CloudWatch logs access
- **Slack API** - Notifications
- **Docker** - Containerization

## Project Structure

```
ai-remediator/
├── remediator.py           # Main application logic
├── Dockerfile             # Container definition
├── .dockerignore          # Docker build optimization
├── requirements.txt       # Python dependencies
├── config.py.template     # Configuration template
└── README.md             # This file
```

## Setup

### Prerequisites
- AWS account with CloudWatch access
- OpenAI API key
- Slack webhook URL
- Python 3.10+
- Docker (optional)

### Local Development
```bash
# Clone and setup
git clone <your-repo-url>
cd ai-remediator
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure credentials
cp config.py.template config.py
# Edit config.py with your actual API keys

# Run the application
python remediator.py
```

### Docker Usage
```bash
# Build the container
docker build -t log-remediation .

# Option 1: Run with config file (easier for development)
docker run -v $(pwd)/config.py:/app/config.py log-remediation

# Option 2: Run with environment variables (more Docker-native)
docker run -e CLOUD_REGION=us-east-1 \
           -e OPENAI_API_KEY=your_openai_key \
           -e SLACK_WEBHOOK_URL=your_slack_webhook \
           -e CLOUD_ACCESS_KEY=your_aws_key \
           -e CLOUD_SECRET_KEY=your_aws_secret \
           log-remediation
```

## Configuration

### Environment Variables
- `CLOUD_REGION` - AWS region (default: us-east-1)
- `OPENAI_API_KEY` - OpenAI API key (required)
- `SLACK_WEBHOOK_URL` - Slack webhook URL (required)
- `CLOUD_ACCESS_KEY` - AWS access key
- `CLOUD_SECRET_KEY` - AWS secret key

## Features

- **Smart retry logic** - Exponential backoff for API failures
- **Error handling** - Graceful degradation when permissions are missing
- **Environment variables** - Supports both local config and environment variables
- **Docker support** - Containerized execution with security best practices
- **Configurable limits** - Process up to 3 log groups by default to control costs

## Error Handling

The application includes:
- **Exponential backoff** for OpenAI API rate limits
- **Graceful degradation** when CloudWatch metrics permissions are missing
- **Comprehensive logging** with timestamps and error details
- **Slack alerts** for critical failures like API quota issues