# Device AI Injection Gateway

This example provides a **practical and safe** interpretation of your request to "inject AI into programs/apps".

Instead of trying to access ChatGPT account sessions (which should not be done), it runs a local gateway that lets **approved apps on your device** call an AI assistant over HTTP.

## What it does

- Runs a local HTTP server with one endpoint: `POST /inject`
- Accepts app requests: `device_id`, `app_name`, `task`, and optional `context`
- Enforces an allow-list with `ALLOWED_APPS`
- Uses `OpenAIChatModel` through AgentScope to generate AI responses

## Quickstart

From repository root:

```bash
export PYTHONPATH=src
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="gpt-4.1-mini"
export ALLOWED_APPS="notes,calendar,mail"
python examples/integration/device_ai_injection_gateway/main.py
```

## Test request

```bash
curl -X POST http://127.0.0.1:8765/inject \
  -H 'Content-Type: application/json' \
  -d '{
    "device_id": "laptop-01",
    "app_name": "notes",
    "task": "Summarize this meeting note and produce 3 action items",
    "context": {"note": "We need to ship onboarding by Friday and align docs."}
  }'
```

## Integrating with your own apps

Your app/plugin only needs to send JSON to the gateway. Example payload:

```json
{
  "device_id": "phone-02",
  "app_name": "calendar",
  "task": "Suggest free slots for a 30-minute 1:1",
  "context": {
    "events": [
      "2026-03-27T09:00:00Z team standup",
      "2026-03-27T13:00:00Z product review"
    ]
  }
}
```

## Important note

This is designed for **consented integrations** in your own software stack. It does not and should not bypass app permissions or access ChatGPT login sessions on other apps/devices.
