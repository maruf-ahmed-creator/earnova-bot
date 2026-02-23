import os
import asyncio

from aiogram import Bot

from db import db, mark_referred_left

def _env_int(name: str) -> int:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} missing in environment variables")
    return int(v)

MAIN_CHANNEL_ID = _env_int("MAIN_CHANNEL_ID")


async def referral_leave_watcher(bot: Bot):
    """Periodically checks whether referred users left MAIN_CHANNEL_ID.
    If they left, points are reverted via mark_referred_left().
    """
    while True:
        try:
            cursor = db.referrals.find({"left_at": None})
            async for r in cursor:
                referred_id = int(r["referred_id"])
                try:
                    member = await bot.get_chat_member(MAIN_CHANNEL_ID, referred_id)
                    if member.status in ["left", "kicked"]:
                        await mark_referred_left(referred_id)
                except Exception:
                    # if Telegram API fails, skip this cycle
                    continue
        except Exception:
            pass

        # run every 10 minutes
        await asyncio.sleep(600)
