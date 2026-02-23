from __future__ import annotations

import asyncio
from datetime import datetime
from aiogram import Bot

from config import settings
from db import db, pending_proofs_due, expire_proof, set_banned, mark_referred_left

async def proof_timeout_worker(bot: Bot):
    while True:
        try:
            due = await pending_proofs_due(datetime.utcnow(), limit=200)
            for p in due:
                await expire_proof(p["_id"])
                uid = int(p["user_id"])
                await set_banned(uid, True)
                try:
                    await bot.send_message(
                        settings.PROOF_CHANNEL_PUBLIC,
                        f"Auto-ban: User {uid} did not submit screenshot in time. Resource={p.get('resource_id')}",
                    )
                except Exception:
                    pass
        except Exception:
            pass
        await asyncio.sleep(60)

async def referral_leave_worker(bot: Bot):
    while True:
        try:
            main = settings.REQUIRED_CHANNEL_ID
            cursor = db.referrals.find({"left_at": None})
            async for r in cursor:
                referred = int(r["referred_id"])
                try:
                    m = await bot.get_chat_member(main, referred)
                    if m.status in ("left", "kicked"):
                        await mark_referred_left(referred)
                except Exception:
                    continue
        except Exception:
            pass
        await asyncio.sleep(600)

async def broadcast_worker(bot: Bot):
    while True:
        try:
            job = await db.broadcast_jobs.find_one({"status": "queued"}, sort=[("created_at", 1)])
            if not job:
                await asyncio.sleep(10)
                continue
            await db.broadcast_jobs.update_one({"_id": job["_id"]}, {"$set": {"status": "running"}})

            text = job["text"]
            sent = 0
            failed = 0
            cursor = db.users.find({}, {"user_id": 1})
            async for u in cursor:
                uid = int(u["user_id"])
                try:
                    await bot.send_message(uid, text)
                    sent += 1
                except Exception:
                    failed += 1
                if (sent + failed) % 25 == 0:
                    await asyncio.sleep(1.2)
            await db.broadcast_jobs.update_one({"_id": job["_id"]}, {"$set": {"status": "done", "sent": sent, "failed": failed}})
        except Exception:
            await asyncio.sleep(10)
