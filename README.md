# Earnova SuperBot (Railway-ready, scalable template)

This is a **scalable** Telegram bot template using:
- **aiogram v3** (async)
- **FastAPI webhook** (recommended for high scale)
- **MongoDB (motor)**
- Optional **Redis** (rate limit + cache)

✅ Implements:
- /start -> required channel join gate (lock if not joined)
- Permanent **Reply Keyboard** menu
- Balance / Referral / Bot Info / Help / Language / Total Users
- Get Resource (safe generic "resource" distribution; only use data you own/are allowed to share)
- Verify buttons (Working / Not Working)
- Screenshot within 10 min -> proof forwarded to channels
- Auto-ban if screenshot not submitted
- Referral +10 on join, -10 if referred user leaves required channel
- "Channel version" lock: adding a new required channel locks everyone until they join+verify

✅ Admin commands (simple & reliable):
- /admin (shows admin help)
- /ch_add <channel_id> <type>
- /ch_remove <channel_id>
- /ch_list
- /points_give <user_id> <points> [note]
- /points_take <user_id> <points> [note]
- /ban <user_id>
- /unban <user_id>
- /res_add <name>|<secret>|<cost>|<default_flag 0/1>
- /res_remove <resource_id>
- /res_list
- /broadcast <text>
- /stats

---

## Railway deploy
1) Create project -> service from GitHub
2) Set **Start Command**:
   ```
   uvicorn app:app --host 0.0.0.0 --port $PORT
   ```
3) Add Variables (see below)
4) Deploy, then set Telegram webhook:
   - Open: `https://<your-railway-domain>/set-webhook` in browser once

---

## Required ENV variables
- BOT_TOKEN
- WEBHOOK_BASE (e.g. https://your-service.up.railway.app)
- MONGO_URI (must include db name, e.g. ...mongodb.net/earnova)
- ENCRYPTION_KEY (Fernet key; see `tools/generate_key.py`)
- REQUIRED_CHANNEL_ID (main required channel id, e.g. -100xxxx)
- PROOF_CHANNEL_PUBLIC (Earnova System channel id)
- PROOF_CHANNEL_DATA (Data channel id)
- ADMIN_IDS (comma-separated, e.g. 12345,67890)

Optional:
- REDIS_URL (if set, rate-limit/cache enabled)
- OPENAI_API_KEY (enables Ask AI)

---

## MongoDB note
Ensure Atlas Network Access allows Railway IP (quick dev: 0.0.0.0/0).

---
## Safety / policy note
This bot is implemented as a **generic resource distribution** system.
Only distribute resources/credentials you **own** or are **authorized** to share.
