# earnova-bot (fixed)

✅ This repo was auto-fixed to restore proper Python formatting and missing modules.

## Quick start (Railway)
- Set **Start Command**: `python main.py`
- Add env vars (see below)
- Deploy

## Required env vars
- BOT_TOKEN
- MONGO_URI  (must include database name, e.g. `...mongodb.net/earnova`)
- ENCRYPTION_KEY (Fernet key)
- MAIN_CHANNEL_ID
- EARNOVA_CHANNEL_ID
- DATA_CHANNEL_ID
- ADMIN_IDS (comma-separated user IDs, optional)

## Notes
- This bot can send stored credentials; **only use accounts/credentials you own or have permission to share**.
