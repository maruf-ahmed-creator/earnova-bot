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
WEBHOOK_URL = f"{settings.WEBHOOK_BASE}{WEBHOOK_PATH}"

@app.on_event("startup")
async def on_startup():
    global bot, dp
    bot, dp = await build_bot_and_dp()
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    await start_background_workers(bot)
    log.info(f"✅ Webhook set: {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    global bot
    if bot:
        await bot.session.close()

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/set-webhook")
async def set_webhook():
    global bot
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    return {"webhook": WEBHOOK_URL}

@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    global dp, bot
    update = Update.model_validate(await req.json())
    await dp.feed_update(bot, update)
    return {"ok": True}
