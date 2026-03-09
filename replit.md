# Earnova SuperBot

A scalable Telegram bot built with aiogram v3, FastAPI (webhook mode), MongoDB (motor), and optional Redis.

## Architecture

- **app.py** — FastAPI app, webhook endpoint, startup/shutdown lifecycle
- **bot.py** — Bot and Dispatcher construction, background worker launch
- **config.py** — Pydantic settings from environment variables
- **db.py** — All MongoDB operations via motor (async)
- **user.py** — User-facing Telegram message/callback handlers (aiogram Router)
- **admin.py** — Admin command handlers
- **scheduler.py** — Background async workers (proof timeout, referral leave, broadcast)
- **join_gate.py** — Required channel join verification logic
- **keyboards.py** — Telegram keyboard definitions
- **rate_limit.py** — Optional Redis-based rate limiting
- **ai.py** — OpenAI chat integration (optional)
- **generate_key.py** — Utility to generate a Fernet encryption key

## Running

Workflow: `uvicorn app:app --host 0.0.0.0 --port 5000`

## Required Environment Secrets

- `BOT_TOKEN` — Telegram bot token from @BotFather
- `WEBHOOK_BASE` — Public HTTPS base URL (e.g. https://your-app.replit.app)
- `MONGO_URI` — MongoDB connection string (must include DB name)
- `ENCRYPTION_KEY` — Fernet key (generate with `python generate_key.py`)
- `REQUIRED_CHANNEL_ID` — Main required Telegram channel ID
- `PROOF_CHANNEL_PUBLIC` — Telegram channel for public proof posts
- `PROOF_CHANNEL_DATA` — Telegram channel for data storage
- `ADMIN_IDS` — Comma-separated Telegram user IDs for admins

## Optional Secrets

- `REDIS_URL` — Enables rate limiting and caching
- `OPENAI_API_KEY` — Enables the Ask AI feature

## Deployment

Configured as `vm` (always-running) deployment target since the bot requires persistent background workers.
After deploying, visit `https://your-domain/set-webhook` once to register the Telegram webhook.
