import os
import logging
from fastapi import FastAPI, Request
from aiogram.types import Update
from config import settings
from bot import build_bot_and_dp, start_background_workers

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("earnova")

app = FastAPI()
bot = None
dp = None

WEBHOOK_PATH = "/webhook"

def get_webhook_base() -> str:
    replit_domain = os.environ.get("REPLIT_DEV_DOMAIN") or os.environ.get("REPLIT_DOMAINS", "").split(",")[0].strip()
    if replit_domain:
        return f"https://{replit_domain}"
    if settings.WEBHOOK_BASE and "telegram" not in settings.WEBHOOK_BASE:
        return settings.WEBHOOK_BASE.rstrip("/")
    raise RuntimeError("Cannot determine webhook base URL. REPLIT_DEV_DOMAIN is not set.")

@app.on_event("startup")
async def on_startup():
    global bot, dp
    bot, dp = await build_bot_and_dp()
    webhook_url = f"{get_webhook_base()}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    await start_background_workers(bot)
    log.info(f"✅ Webhook set: {webhook_url}")

@app.on_event("shutdown")
async def on_shutdown():
    global bot
    if bot:
        await bot.session.close()

@app.get("/")
async def root():
    return {"status": "running", "webhook": WEBHOOK_PATH}

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/set-webhook")
async def set_webhook():
    global bot
    webhook_url = f"{get_webhook_base()}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    return {"webhook": webhook_url}

@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    global dp, bot
    try:
        update = Update.model_validate(await req.json())
        await dp.feed_update(bot, update)
    except Exception as e:
        log.exception(f"Error processing update: {e}")
    return {"ok": True}
