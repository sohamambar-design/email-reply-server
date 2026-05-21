# Smart Email Reply Agent - Flask Backend

Production-ready Flask backend that analyzes incoming emails with the Gemini API and returns a structured JSON classification.

## Features

- REST API endpoint: `POST /generate-reply`
- Modular folder structure (routes, services, utils)
- Input validation and sanitization
- Gemini prompt engineering for deterministic JSON classification
- Proper HTTP status codes and JSON responses
- Centralized logging
- CORS enabled for frontend integration
- Embedded Gemini API key usage in the service layer
- Optional user context enrichment

## Project Structure

project/
|
|-- app.py
|-- routes/
| |-- email_routes.py
|-- services/
| |-- gemini_service.py
|-- utils/
| |-- validators.py
|-- .env
|-- requirements.txt
|-- README.md

## Prerequisites

- Python 3.10+
- Gemini API key from Google AI Studio

## Setup Instructions

1. Create and activate virtual environment:

```bash
python -m venv .venv
# Windows PowerShell
.\\.venv\\Scripts\\Activate.ps1
# macOS/Linux
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Optional local settings in `.env`:

```env
FLASK_DEBUG=false
PORT=5000
LOG_LEVEL=INFO
```

4. Run the server:

```bash
python app.py
```

Server starts at: `http://localhost:5000`

## API Endpoint

### POST `/generate-reply`

Analyzes incoming email text and returns a structured JSON object with category, summary, and reply draft when applicable.

### Request Body (Example)

```json
{
  "email_id": "1001",
  "email_content": "From: manager@example.com\nSubject: Project Details\n\nCan you send me the latest project details and timeline?",
  "user_data": {
    "name": "John Doe",
    "designation": "Software Engineer",
    "company": "ABC Tech",
    "current_projects": ["AI CRM System", "Email Automation Tool"],
    "timeline": "Project expected completion by next Friday",
    "tone_preference": "professional"
  },
  "reply_mode": "short",
  "include_signature": true
}
```

### Success Response

```json
{
  "category": "replyable",
  "summary": "The sender asks for the latest project details and timeline for the ongoing work.",
  "reply_draft": "Hi Manager,\n\nPlease find the latest project details and updated timeline below...\n\nBest Regards,\nJohn Doe",
  "email_id": "1001",
  "signature": true
}
```

## Error Responses

- `400 Bad Request`: Validation errors
- `415 Unsupported Media Type`: Non-JSON request
- `500 Internal Server Error`: Server/config issues
- `502 Bad Gateway`: Gemini API failure

## cURL Testing Example

```bash
curl -X POST "http://localhost:5000/generate-reply" \\
  -H "Content-Type: application/json" \\
  -d '{
    "email_id": "1001",
    "email_content": "From: manager@example.com\nSubject: Project Details\n\nCan you send me the latest project details and timeline?",
    "user_data": {
      "name": "John Doe",
      "designation": "Software Engineer",
      "company": "ABC Tech",
      "current_projects": ["AI CRM System", "Email Automation Tool"],
      "timeline": "Project expected completion by next Friday",
      "tone_preference": "professional"
    },
    "reply_mode": "short",
    "include_signature": true
  }'
```

## Postman Testing

1. Method: `POST`
2. URL: `http://localhost:5000/generate-reply`
3. Headers: `Content-Type: application/json`
4. Body: `raw` -> `JSON`
5. Paste the same sample JSON from this README

Optional health check:

- Method: `GET`
- URL: `http://localhost:5000/health`

## Notes for Production

- If you later move the Gemini key out of code, store it in secure environment config and update the service accordingly
- Run behind a production WSGI server (e.g., Gunicorn) and reverse proxy
- Restrict CORS origins based on frontend domain
- Add rate limiting and authentication for public deployments
