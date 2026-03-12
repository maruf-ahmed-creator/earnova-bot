# db.py
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from cryptography.fernet import Fernet
from pymongo import ReturnDocument

from config import settings

log = logging.getLogger("earnova")

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client.get_default_database()

_fernet = Fernet(settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY)


async def ensure_indexes():
    try:
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index("referrer_id")
        await db.users.create_index("last_active")
        await db.resources.create_index("status")
        await db.proofs.create_index([("user_id", 1), ("status", 1)])
        await db.proofs.create_index("deadline")
        await db.channels.create_index("channel_id", unique=True)
    except Exception:
        pass


def encrypt_secret(plain: str) -> str:
    return _fernet.encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    try:
        return _fernet.decrypt(token.encode()).decode()
    except Exception:
        return "(decryption error)"


async def upsert_user(user_id: int, username: str | None, referrer_id: int | None = None):
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


async def set_user_lang(user_id: int, lang: str):
    await set_language(user_id, lang)


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


async def referral_counts(user_id: int) -> int:
    user = await get_user(user_id)
    return int(user.get("referral_count", 0)) if user else 0


async def inc_points(user_id: int, delta: int):
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$inc": {"points": delta},
            "$set": {"last_active": datetime.utcnow()},
            "$setOnInsert": {"created_at": datetime.utcnow(), "user_id": user_id},
        },
        upsert=True,
    )


async def set_banned(user_id: int, banned: bool):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"banned": banned, "last_active": datetime.utcnow()}},
        upsert=True,
    )


async def inc_accounts_taken(user_id: int, delta: int = 1):
    await db.users.update_one(
        {"user_id": user_id},
        {"$inc": {"accounts_taken": delta}, "$set": {"last_active": datetime.utcnow()}},
    )


async def add_channel(channel_id: int, ch_type: str):
    now = datetime.utcnow()
    await db.channels.update_one(
        {"channel_id": channel_id},
        {"$set": {"channel_id": channel_id, "type": ch_type, "updated_at": now},
         "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    await _bump_required_version()


async def remove_channel(channel_id: int):
    await db.channels.delete_one({"channel_id": channel_id})
    await _bump_required_version()


async def list_channels() -> List[dict]:
    cursor = db.channels.find({})
    return await cursor.to_list(length=None)


async def _bump_required_version():
    now = int(datetime.utcnow().timestamp())
    await db.config.update_one(
        {"key": "required_version"},
        {"$set": {"value": now}},
        upsert=True,
    )


async def get_required_version() -> int:
    doc = await db.config.find_one({"key": "required_version"})
    if doc:
        return int(doc.get("value", 1))
    return 1


async def add_resource(name: str, secret_plain: str, cost: int = 0, default_flag: bool = False) -> ObjectId:
    encrypted = encrypt_secret(secret_plain)
    doc = {
        "name": name,
        "secret": encrypted,
        "cost": cost,
        "default_flag": default_flag,
        "status": "available",
        "created_at": datetime.utcnow(),
    }
    result = await db.resources.insert_one(doc)
    return result.inserted_id


async def remove_resource(resource_id: str) -> bool:
    try:
        oid = ObjectId(resource_id)
    except Exception:
        return False
    result = await db.resources.delete_one({"_id": oid})
    return result.deleted_count > 0


async def list_resources(limit: int = 30) -> List[dict]:
    cursor = db.resources.find({}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def count_available_resources() -> int:
    return await db.resources.count_documents({"status": "available"})


async def claim_resource_for_user(user_id: int) -> Optional[dict]:
    now = datetime.utcnow()
    avail = await db.resources.count_documents({"status": "available"})
    log.info(f"claim_resource_for_user: user={user_id}, available_count={avail}")
    if avail == 0:
        return None
    resource = await db.resources.find_one_and_update(
        {"status": "available"},
        {"$set": {"status": "assigned", "assigned_to": user_id, "assigned_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    log.info(f"claim_resource_for_user: result={'found' if resource else 'None'} id={resource.get('_id') if resource else 'N/A'}")
    return resource


async def create_pending_proof(user_id: int, resource_id: str, status: str, deadline: datetime):
    await db.proofs.insert_one({
        "user_id": user_id,
        "resource_id": resource_id,
        "status": status,
        "type": None,
        "file_id": None,
        "deadline": deadline,
        "created_at": datetime.utcnow(),
        "posted": [],
    })


async def attach_proof_file(user_id: int, file_id: str) -> Optional[dict]:
    proof = await db.proofs.find_one_and_update(
        {"user_id": user_id, "status": "pending"},
        {"$set": {"file_id": file_id, "status": "submitted", "submitted_at": datetime.utcnow()}},
        sort=[("created_at", -1)],
        return_document=True,
    )
    return proof


async def pending_proofs_due(now: datetime, limit: int = 200) -> List[dict]:
    cursor = db.proofs.find({"status": "pending", "deadline": {"$lte": now}}).limit(limit)
    return await cursor.to_list(length=limit)


async def expire_proof(proof_id: ObjectId):
    await db.proofs.update_one(
        {"_id": proof_id},
        {"$set": {"status": "expired", "expired_at": datetime.utcnow()}},
    )


async def free_resource_by_proof(proof: dict):
    """Release an assigned resource back to available when proof expires."""
    rid_str = proof.get("resource_id")
    if not rid_str:
        return
    try:
        oid = ObjectId(rid_str)
    except Exception:
        return
    await db.resources.update_one(
        {"_id": oid, "status": "assigned"},
        {"$set": {"status": "available", "assigned_to": None, "assigned_at": None}},
    )


async def reset_all_stuck_resources() -> int:
    """Admin utility: free all resources stuck in 'assigned' with no active pending proof."""
    result = await db.resources.update_many(
        {"status": "assigned"},
        {"$set": {"status": "available", "assigned_to": None, "assigned_at": None}},
    )
    return result.modified_count


async def mark_referred_left(referred_id: int):
    now = datetime.utcnow()
    referral = await db.referrals.find_one({"referred_id": referred_id, "left_at": None})
    if not referral:
        return
    await db.referrals.update_one(
        {"_id": referral["_id"]},
        {"$set": {"left_at": now}},
    )
    referrer_id = referral.get("referrer_id")
    if referrer_id:
        pts = int(referral.get("points_awarded", 10))
        await db.users.update_one(
            {"user_id": int(referrer_id)},
            {"$inc": {"points": -pts}},
        )
