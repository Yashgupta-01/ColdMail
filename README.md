# ColdMail 📧

A sophisticated, personalized cold email outreach system designed for scale. ColdMail automates the generation, personalization, and delivery of high-conversion cold emails using advanced LLM-driven templates and multi-provider SMTP rotation.

## Overview

ColdMail is a production-grade Python backend for automated cold email campaigns. It combines:
- **AI-Powered Personalization**: LLM-driven email generation based on prospect context
- **Multi-Provider SMTP Rotation**: Distribute sends across multiple email providers to maximize deliverability
- **Template System**: Jinja2-based dynamic templates with variable injection
- **Prospect Enrichment**: Integration with web scraping and data enrichment APIs
- **Delivery Tracking**: Monitor send status, bounces, and engagement metrics
- **Rate Limiting & Warmup**: Intelligent send scheduling to maintain sender reputation

## Features

### Core Capabilities
- **Batch Email Generation**: Process 100s-1000s of prospects in single campaign runs
- **Dynamic Personalization**: 
  - Company-specific research injection
  - Role-based template variations
  - Industry/vertical customization
  - Multi-variable interpolation
- **SMTP Provider Rotation**:
  - Support for Gmail, Office 365, custom SMTP servers
  - Automatic failover on send errors
  - Per-provider rate limiting
  - Credential rotation for deliverability

### Prospect Management
- **CSV/Excel Import**: Load prospect lists (emails, names, company, role, etc.)
- **Data Validation**: Email format checking, domain verification
- **Duplicate Detection**: Prevent sending to same prospect multiple times
- **Enrichment**: Optional company research and job title scraping

### Campaign Management
- **Template Library**: Create and reuse email templates
- **A/B Testing Support**: Multiple template variants with tracking
- **Send Scheduling**: Stagger emails across time zones and hours
- **Delivery Reporting**: Success/failure logs with detailed error messages
- **Retry Logic**: Configurable retry attempts for transient failures

### Deliverability
- **Warm-up Mode**: Gradual send ramp-up to establish sender reputation
- **SPF/DKIM/DMARC Support**: Headers properly configured for authentication
- **Unsubscribe Handling**: Automatic list cleaning based on bounce/complaint feedback
- **Spam Filter Bypass**: Template techniques to minimize spam folder placement

## Tech Stack

- **Language**: Python 3.9+
- **Framework**: FastAPI (for REST API)
- **Email**: SMTP (multi-provider support), sendgrid optional
- **Data**: Pandas, openpyxl (for CSV/Excel processing)
- **Templates**: Jinja2 (dynamic email generation)
- **AI/LLM**: OpenAI / Anthropic / Gemini API (for prospect research + personalization)
- **Database**: SQLite / PostgreSQL (campaign & send tracking)
- **Task Queue**: Celery (async email dispatch)
- **Logging**: Python logging + structured logs

## Project Structure

ColdMail/

├── backend/

│   ├── main.py                 # FastAPI app entry point

│   ├── requirements.txt         # Python dependencies

│   ├── config.py              # Configuration (SMTP, API keys)

│   ├── .env.example           # Environment variables template

│   ├── models/

│   │   ├── prospect.py        # Prospect data model

│   │   ├── campaign.py        # Campaign model

│   │   └── send_log.py        # Send tracking model

│   ├── services/

│   │   ├── email_service.py   # SMTP + send logic

│   │   ├── personalization.py # LLM-driven personalization

│   │   ├── enrichment.py      # Prospect enrichment (web scraping)

│   │   └── template_engine.py # Jinja2 template rendering

│   ├── api/

│   │   ├── campaigns.py       # Campaign CRUD endpoints

│   │   ├── prospects.py       # Prospect import/management

│   │   ├── sends.py          # Send execution endpoints

│   │   └── reports.py        # Analytics/reporting endpoints

│   ├── tasks/

│   │   ├── send_emails.py    # Celery task for async dispatch

│   │   └── retry_failed.py   # Automatic retry task

│   ├── utils/

│   │   ├── email_validator.py # Email format/domain validation

│   │   ├── logger.py         # Centralized logging

│   │   └── decorators.py     # Auth, rate limiting decorators

│   └── tests/

│       ├── test_email_service.py

│       ├── test_personalization.py

│       └── test_api.py

├── migrations/                 # Database migrations (Alembic)

├── templates/                 # Email template examples

│   ├── cold_outreach_v1.html

│   ├── follow_up_v1.html

│   └── demo_prospect_list.csv

├── docs/

│   ├── API.md                # API documentation

│   ├── SETUP.md              # Detailed setup guide

│   └── TEMPLATES.md          # Template creation guide

├── docker-compose.yml        # Docker orchestration

├── Dockerfile               # Container image

├── LICENSE                  # Apache 2.0

└── README.md               # This file

## Installation

### Prerequisites
- Python 3.9+
- PostgreSQL 12+ or SQLite (default)
- Redis (for Celery task queue)
- SMTP credentials (Gmail, Office 365, or custom server)

### Local Setup

1. **Clone the repository**
```bash
   git clone https://github.com/Yashgupta-01/ColdMail.git
   cd ColdMail
```

2. **Create virtual environment**
```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
   cd backend
   pip install -r requirements.txt
```

4. **Configure environment**
```bash
   cp .env.example .env
   # Edit .env with your settings:
   # - SMTP credentials
   # - API keys (OpenAI, Gemini, etc.)
   # - Database URL
   # - Secret key
```

5. **Initialize database**
```bash
   python -m alembic upgrade head
```

6. **Run the application**
```bash
   # Terminal 1: FastAPI server
   uvicorn main:app --reload --port 8000
   
   # Terminal 2: Celery worker (for async sends)
   celery -A tasks worker -l info
```

   Server runs at: `http://localhost:8000`

### Docker Setup (Recommended for Production)

```bash
docker-compose up -d
```

Includes FastAPI, Celery worker, Redis, and PostgreSQL containers.

## Configuration

### Email Providers

#### Gmail (with App Password)
```python
# .env
SMTP_PROVIDER=gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

#### Office 365
```python
# .env
SMTP_PROVIDER=office365
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@company.com
SMTP_PASSWORD=your-password
```

#### Custom SMTP
```python
# .env
SMTP_PROVIDER=custom
SMTP_HOST=mail.custom-domain.com
SMTP_PORT=587
SMTP_USER=username
SMTP_PASSWORD=password
SMTP_USE_TLS=true
```

### Multi-Provider Rotation

```python
# config.py
SMTP_PROVIDERS = [
    {
        "name": "gmail_1",
        "host": "smtp.gmail.com",
        "port": 587,
        "user": "user1@gmail.com",
        "password": "app-password-1"
    },
    {
        "name": "gmail_2",
        "host": "smtp.gmail.com",
        "port": 587,
        "user": "user2@gmail.com",
        "password": "app-password-2"
    }
]
```

## API Reference

### Create Campaign
```bash
POST /api/campaigns/
Content-Type: application/json

{
  "name": "YC Founders Q1 2024",
  "template_id": "cold_outreach_v1",
  "subject_line": "Quick idea for {company_name}",
  "send_limit_per_hour": 50,
  "schedule": {
    "start_date": "2024-01-15",
    "end_date": "2024-01-31",
    "timezone": "America/New_York"
  }
}
```

### Import Prospects
```bash
POST /api/prospects/import/
Content-Type: multipart/form-data

Form Data:
- file: prospect_list.csv (columns: email, first_name, company, job_title, etc.)
- campaign_id: 1
```

### Execute Campaign
```bash
POST /api/campaigns/{campaign_id}/send/
Content-Type: application/json

{
  "dry_run": false,
  "personalization_prompt": "Focus on ROI benefits specific to {industry}"
}
```

Response:
```json
{
  "campaign_id": 1,
  "total_queued": 245,
  "task_id": "send-campaign-001",
  "status": "queued"
}
```

### Get Send Report
```bash
GET /api/campaigns/{campaign_id}/report/

Response:
{
  "campaign_id": 1,
  "total_sent": 240,
  "successful": 238,
  "failed": 2,
  "bounced": 1,
  "open_rate": 0.32,
  "click_rate": 0.08,
  "reply_rate": 0.05,
  "send_logs": [...]
}
```

Full API docs available at `/docs` (Swagger UI) after server start.

## Email Templates

### Template Syntax (Jinja2)

```html
<h1>Hi {{ first_name }},</h1>

<p>I was researching {{ company_name }} and noticed you're in {{ job_title }}.</p>

{% if industry == "SaaS" %}
  <p>Your company's focus on {{ primary_product }} aligns with our platform's strengths in {{ our_strength }}.</p>
{% endif %}

<p>I'd love to chat about how we've helped similar companies increase {{ metric }} by {{ improvement }}%.</p>

<p>Free 15-min call? <a href="{{ calendar_link }}">Calendar here</a></p>

<p>Cheers,<br>{{ sender_name }}</p>
```

### Creating Custom Templates

1. Create HTML template in `templates/` folder
2. Use `{{ variable_name }}` for dynamic content
3. Conditionals: `{% if condition %} ... {% endif %}`
4. Loops: `{% for item in items %} ... {% endfor %}`
5. Register in campaign configuration

See `docs/TEMPLATES.md` for advanced template techniques.

## Usage Examples

### Campaign A: VCs Cold Outreach
```python
from api.campaigns import create_campaign
from services.email_service import send_campaign

# Create campaign
campaign = create_campaign(
    name="VC Cold Outreach Q1",
    template_id="vc_cold_call",
    prospects_file="vc_list.csv",
    send_limit_per_hour=20
)

# Enrich prospects with company info
enrich_prospects(campaign.id, lookup_company_info=True)

# Execute sends (async)
send_campaign(campaign.id, personalization_enabled=True)
```

### Campaign B: Follow-up Sequences
```python
# Create follow-up campaign based on original responses
follow_up = create_campaign(
    name="VC Follow-up (No Reply)",
    template_id="follow_up_v1",
    prospects_filter={"replied": False, "days_since_send": 5}
)

send_campaign(follow_up.id)
```

## Performance & Deliverability

### Best Practices
- **Warm-up**: Start with 10-20 emails/hour; gradually increase
- **Content**: Personalized, specific (not "mass mail" generic)
- **Headers**: Ensure SPF, DKIM, DMARC records are in place
- **Send Timing**: Stagger across business hours (9AM-5PM recipient timezone)
- **List Quality**: Remove invalid/temporary email addresses

### Monitoring
- Track delivery rates by SMTP provider
- Monitor bounce reasons (hard vs soft bounces)
- Segment unresponsive lists (exclude after 2 weeks no reply)

## Troubleshooting

### SMTP Connection Errors
SMTPAuthenticationError: 535 Authentication failed
- Verify credentials in `.env`
- For Gmail: Use app-specific password (2FA required)
- For Office 365: Ensure Modern Auth is enabled

### High Bounce Rate
- Run email validation on list: `python scripts/validate_emails.py prospect_list.csv`
- Check SPF/DKIM records: `tools/check_email_auth.py yourdomain.com`
- Review template for spam keywords (see `docs/SPAM_FILTER_TIPS.md`)

### Slow Send Speed
- Increase `SEND_LIMIT_PER_HOUR` in config
- Ensure Redis is running: `redis-cli ping`
- Check Celery worker logs for bottlenecks

## Contributing

Contributions welcome! Areas of focus:
- Additional SMTP providers (Sendgrid, Mailgun)
- Analytics dashboard
- Reply detection & auto-segmentation
- Template A/B testing framework
- Webhook integrations (CRM sync)

Process:
1. Fork the repo
2. Create feature branch (`git checkout -b feature/your-feature`)
3. Write tests for new functionality
4. Commit (`git commit -m 'Add feature'`)
5. Push (`git push origin feature/your-feature`)
6. Submit Pull Request

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_email_service.py

# With coverage
pytest --cov=backend tests/
```

## Security

- **API Key Storage**: Never commit `.env` file
- **Email Credentials**: Rotate regularly; use service accounts
- **Rate Limiting**: Built-in per-IP rate limits on POST endpoints
- **Input Validation**: All prospect data sanitized before template injection
- **CORS**: Configured for specific domains only (no wildcard)

## License

This project is licensed under the Apache License 2.0—see the [LICENSE](LICENSE) file for details.

## Roadmap

- [ ] Web dashboard for campaign management
- [ ] ML-based send time optimization
- [ ] Native Slack/Discord integrations
- [ ] Reply parsing & CRM sync
- [ ] Multi-language email support
- [ ] Phone number validation & SMS fallback

## Contact & Support

For issues, questions, or partnerships:
- Open an [Issue](https://github.com/Yashgupta-01/ColdMail/issues)
- Email: yashgupta01.dev@gmail.com
- LinkedIn: [Yash Gupta](https://linkedin.com/in/yashgupta-dev)

---

**Scale your outreach responsibly.** 📧
