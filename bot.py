import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from config import settings
from db import ensure_indexes
from user import router as user_router
from admin import router as admin_router
from workers.scheduler import proof_timeout_worker, referral_leave_worker, broadcast_worker

log = logging.getLogger("earnova")

async def build_bot_and_dp():
    bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(admin_router)
    dp.include_router(user_router)
    await ensure_indexes()
    return bot, dp

async def start_background_workers(bot: Bot):
    import asyncio
    asyncio.create_task(proof_timeout_worker(bot))
    asyncio.create_task(referral_leave_worker(bot))
    asyncio.create_task(broadcast_worker(bot))
    log.info("✅ Background workers started")
