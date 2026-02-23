from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List

import motor.motor_asyncio
from bson import ObjectId
from cryptography.fernet import Fernet

from config import settings

client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URI)
db = client.get_default_database()

fernet = Fernet(settings.ENCRYPTION_KEY.encode())

async def ensure_indexes():
    await db.users.create_index("user_id", unique=True)
    await db.users.create_index("created_at")
    await db.resources.create_index([("status", 1), ("created_at", 1)])
    await db.resources.create_index("assigned_to")
    await db.referrals.create_index("referred_id")
    await db.referrals.create_index("referrer_id")
    await db.referrals.create_index("left_at")
    await db.proofs.create_index([("user_id", 1), ("created_at", -1)])
    await db.proofs.create_index("deadline_at")
    await db.channels.create_index("channel_id", unique=True)

async def upsert_user(user_id: int, username: Optional[str], referrer_id: Optional[int] = None) -> Dict[str, Any]:
    now = datetime.utcnow()
    doc = {
        "user_id": int(user_id),
        "username": username,
        "language": "bn",
        "points": 0,
        "banned": False,
        "accounts_taken": 0,
        "created_at": now,
        "last_active": now,
        "referrer_id": int(referrer_id) if referrer_id else None,
        "joined_required_version": 0,
    }
    await db.users.update_one(
        {"user_id": int(user_id)},
        {"$setOnInsert": doc, "$set": {"last_active": now}},
        upsert=True,
    )
    return await db.users.find_one({"user_id": int(user_id)})

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    return await db.users.find_one({"user_id": int(user_id)})

async def set_user_lang(user_id: int, lang: str):
    await db.users.update_one({"user_id": int(user_id)}, {"$set": {"language": lang}})

async def inc_points(user_id: int, delta: int):
    await db.users.update_one({"user_id": int(user_id)}, {"$inc": {"points": int(delta)}})

async def set_banned(user_id: int, banned: bool):
    await db.users.update_one({"user_id": int(user_id)}, {"$set": {"banned": bool(banned)}})

async def inc_accounts_taken(user_id: int, delta: int = 1):
    await db.users.update_one({"user_id": int(user_id)}, {"$inc": {"accounts_taken": int(delta)}})

async def set_joined_required_version(user_id: int, v: int):
    await db.users.update_one({"user_id": int(user_id)}, {"$set": {"joined_required_version": int(v)}})

# Channels
async def get_required_version() -> int:
    doc = await db.meta.find_one({"_id": "required_channels_version"})
    return int(doc["v"]) if doc and "v" in doc else 0

async def bump_required_version():
    v = await get_required_version()
    await db.meta.update_one({"_id": "required_channels_version"}, {"$set": {"v": v + 1}}, upsert=True)

async def add_channel(channel_id: int, ch_type: str):
    await db.channels.update_one(
        {"channel_id": int(channel_id)},
        {"$set": {"channel_id": int(channel_id), "type": ch_type, "active": True, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    if ch_type == "required":
        await bump_required_version()

async def remove_channel(channel_id: int):
    doc = await db.channels.find_one({"channel_id": int(channel_id)})
    if doc and doc.get("type") == "required":
        await bump_required_version()
    await db.channels.delete_one({"channel_id": int(channel_id)})

async def list_channels() -> List[Dict[str, Any]]:
    return await db.channels.find({}).to_list(length=500)

# Resources
async def add_resource(name: str, secret_plain: str, cost: int = 0, default_flag: bool = False) -> ObjectId:
    enc = fernet.encrypt(secret_plain.encode()).decode()
    doc = {
        "name": name,
        "secret": enc,
        "cost": int(cost),
        "default_flag": bool(default_flag),
        "status": "available",
        "assigned_to": None,
        "assigned_at": None,
        "created_at": datetime.utcnow(),
    }
    res = await db.resources.insert_one(doc)
    return res.inserted_id

async def remove_resource(resource_id: str) -> bool:
    try:
        oid = ObjectId(resource_id)
    except Exception:
        return False
    r = await db.resources.update_one({"_id": oid}, {"$set": {"status": "removed"}})
    return r.modified_count > 0

async def list_resources(limit: int = 30) -> List[Dict[str, Any]]:
    return await db.resources.find({}).sort("created_at", -1).limit(limit).to_list(length=limit)

async def claim_resource_for_user(user_id: int) -> Optional[Dict[str, Any]]:
    doc = await db.resources.find_one_and_update(
        {"status": "available"},
        {"$set": {"status": "assigned", "assigned_to": int(user_id), "assigned_at": datetime.utcnow()}},
        sort=[("created_at", 1)],
        return_document=True,
    )
    return doc

def decrypt_secret(cipher: str) -> str:
    return fernet.decrypt(cipher.encode()).decode()

# Referrals
async def mark_referred_left(referred_id: int):
    r = await db.referrals.find_one({"referred_id": int(referred_id), "left_at": None})
    if not r:
        return
    await db.referrals.update_one({"_id": r["_id"]}, {"$set": {"left_at": datetime.utcnow()}})
    await inc_points(int(r["referrer_id"]), -int(r.get("points_awarded", 10)))

async def referral_counts(user_id: int) -> int:
    return await db.referrals.count_documents({"referrer_id": int(user_id)})

# Proofs
async def create_pending_proof(user_id: int, resource_id: str, proof_type: str, deadline_at: datetime):
    doc = {
        "user_id": int(user_id),
        "resource_id": resource_id,
        "type": proof_type,
        "file_id": None,
        "posted": [],
        "created_at": datetime.utcnow(),
        "deadline_at": deadline_at,
        "status": "pending",
    }
    await db.proofs.insert_one(doc)

async def attach_proof_file(user_id: int, file_id: str) -> Optional[Dict[str, Any]]:
    p = await db.proofs.find_one({"user_id": int(user_id), "status": "pending"}, sort=[("created_at", -1)])
    if not p:
        return None
    await db.proofs.update_one({"_id": p["_id"]}, {"$set": {"file_id": file_id, "status": "received"}})
    return await db.proofs.find_one({"_id": p["_id"]})

async def pending_proofs_due(now: datetime, limit: int = 200):
    return await db.proofs.find({"status": "pending", "deadline_at": {"$lte": now}}).limit(limit).to_list(length=limit)

async def expire_proof(_id):
    await db.proofs.update_one({"_id": _id}, {"$set": {"status": "expired"}})
