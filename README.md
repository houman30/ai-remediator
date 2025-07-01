# AI Log Remediation Tool

A DevOps project that analyzes AWS CloudWatch log groups using OpenAI and sends insights via Slack. Built with modern DevOps practices including containerization, CI/CD, and infrastructure as code.

## Architecture

```
GitHub Actions → Docker/ECR → AWS Lambda → CloudWatch Logs
                                    ↓
                               OpenAI Analysis
                                    ↓
                              Slack Notifications
```

## Tech Stack

- **Runtime**: Python 3.10, AWS Lambda
- **AI**: OpenAI GPT-3.5 for log analysis  
- **Infrastructure**: Docker, Terraform, GitHub Actions
- **Monitoring**: CloudWatch metrics and alerts
- **Notifications**: Slack integration

## DevOps Features

- **Containerization** - Docker with security best practices
- **CI/CD Pipeline** - Automated testing and deployment
- **Infrastructure as Code** - Terraform for AWS resources
- **Monitoring** - Custom CloudWatch metrics
- **Error Handling** - Exponential backoff and graceful degradation

## Quick Start

### Local Development
```bash
# Setup
git clone <repo-url>
cd ai-remediator
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure
cp config.py.template config.py
# Add your API keys to config.py

# Run
python remediator.py
```

### Docker
```bash
docker build -t log-remediation .
docker run -e OPENAI_API_KEY=your_key \
           -e SLACK_WEBHOOK_URL=your_webhook \
           log-remediation
```

## Configuration

Set these environment variables:
- `CLOUD_REGION` - AWS region (default: us-east-1)
- `OPENAI_API_KEY` - OpenAI API key
- `SLACK_WEBHOOK_URL` - Slack webhook for notifications
- `CLOUD_ACCESS_KEY` / `CLOUD_SECRET_KEY` - AWS credentials (local only)

## What It Does

1. **Fetches** CloudWatch log groups from AWS
2. **Analyzes** each log group using OpenAI GPT-3.5
3. **Reports** findings via Slack with timing metrics
4. **Tracks** performance in CloudWatch metrics
5. **Handles** errors gracefully with retry logic

## Deployment

### Manual
```bash
# Deploy infrastructure
cd terraform && terraform apply

# Deploy code via CI/CD
git push origin main
```

### Automated
- Push to `main` triggers GitHub Actions
- Tests code quality and builds Docker image
- Pushes to AWS ECR and updates Lambda

## Monitoring

Tracks key metrics in CloudWatch:
- API response times and success rates
- Processing duration and throughput  
- Error rates and retry attempts
- Slack notification delivery

## Why This Project?

**Demonstrates real DevOps skills:**
- Building production-ready applications
- Implementing proper CI/CD pipelines
- Managing cloud infrastructure with code
- Creating observable, maintainable systems

**Business value:**
- Automates manual log analysis
- Provides consistent insights across teams
- Reduces time to identify log issues

## Project Structure

```
ai-remediator/
├── remediator.py              # Main application
├── Dockerfile                # Container definition  
├── requirements.txt          # Dependencies
├── .github/workflows/ci.yml  # CI/CD pipeline
├── terraform/               # Infrastructure code
└── config.py.template      # Configuration template
```

## Next Steps

- Multi-region support
- Custom analysis prompts
- Cost optimization dashboard
- Integration with incident management tools

## License

MIT License - see [LICENSE](LICENSE) file for details.