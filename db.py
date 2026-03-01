# db.py
from __future__ import annotations

from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

from config import settings

# Mongo client
client = AsyncIOMotorClient(settings.MONGO_URI)
db = client.get_default_database()


async def ensure_indexes():
    """
    Optional: indexes create (safe). Call at startup if you want.
    """
    try:
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index("referrer_id")
        await db.users.create_index("last_active")
    except Exception:
        # index already exists or no permission—ignore
        pass


async def upsert_user(user_id: int, username: str | None, referrer_id: int | None = None):
    """
    Fix: last_active conflict remove করা হয়েছে ✅
    - last_active শুধু $set এ থাকবে
    - created_at শুধু $setOnInsert এ থাকবে
    """
    now = datetime.utcnow()

    update_doc = {
        "$set": {
            "username": username,
            "last_active": now,
        },
        "$setOnInsert": {
            "user_id": user_id,
            "created_at": now,
        },
    }

    # referrer_id only on first insert
    if referrer_id:
        update_doc["$setOnInsert"]["referrer_id"] = referrer_id

    await db.users.update_one({"user_id": user_id}, update_doc, upsert=True)


async def get_user(user_id: int):
    return await db.users.find_one({"user_id": user_id})


async def set_language(user_id: int, lang: str):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"language": lang, "last_active": datetime.utcnow()}},
        upsert=True,
    )


async def add_balance(user_id: int, amount: int):
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$inc": {"balance": int(amount)},
            "$set": {"last_active": datetime.utcnow()},
            "$setOnInsert": {"created_at": datetime.utcnow(), "user_id": user_id},
        },
        upsert=True,
    )


async def inc_referral(referrer_id: int):
    await db.users.update_one(
        {"user_id": referrer_id},
        {
            "$inc": {"referral_count": 1},
            "$set": {"last_active": datetime.utcnow()},
            "$setOnInsert": {"created_at": datetime.utcnow(), "user_id": referrer_id},
        },
        upsert=True,
    )
