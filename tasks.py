import os
import asyncio
from db import db, mark_referred_left

CHECK_INTERVAL = 60  # seconds

async def referral_leave_watcher(bot):
    main_channel = int(os.getenv("MAIN_CHANNEL_ID"))

    while True:
        try:
            cursor = db.referrals.find({"left_at": None})
            async for r in cursor:
                referred_id = int(r["referred_id"])
                try:
                    member = await bot.get_chat_member(main_channel, referred_id)
                    if member.status in ["left", "kicked"]:
                        await mark_referred_left(referred_id)
                except:
                    pass
        except:
            pass

        await asyncio.sleep(CHECK_INTERVAL)
