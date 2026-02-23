import os
from datetime import datetime

import motor.motor_asyncio
from bson import ObjectId
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI missing in environment variables")

ENCRYPTION_KEY_RAW = os.getenv("ENCRYPTION_KEY", "")
if not ENCRYPTION_KEY_RAW:
    raise RuntimeError("ENCRYPTION_KEY missing in environment variables")

ENCRYPTION_KEY = ENCRYPTION_KEY_RAW.encode()

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)

# NOTE: get_default_database() needs a DB name in the URI, e.g. mongodb+srv://.../mydb
db = client.get_default_database()

fernet = Fernet(ENCRYPTION_KEY)


# Users
async def get_user(user_id: int):
    return await db.users.find_one({"user_id": int(user_id)})


async def create_user_doc(user_id: int, username=None, referrer_id=None):
    doc = {
        "user_id": int(user_id),
        "username": username,
        "language": "bn",
        "points": 0,
        "referrer_id": int(referrer_id) if referrer_id else None,
        "accounts_taken": [],
        "banned": False,
        "joined_channels": [],
        "created_at": datetime.utcnow(),
        "last_active": datetime.utcnow(),
    }
    await db.users.update_one({"user_id": int(user_id)}, {"$setOnInsert": doc}, upsert=True)
    return await get_user(user_id)


# Accounts
async def add_account_doc(account_name: str, credential_plain: str, points_cost=0, default_flag=False):
    enc = fernet.encrypt(credential_plain.encode()).decode()
    doc = {
        "account_name": account_name,
        "credential": enc,
        "points_cost": int(points_cost),
        "default_flag": bool(default_flag),
        "status": "available",
        "assigned_to": None,
        "assigned_at": None,
        "created_at": datetime.utcnow(),
    }
    res = await db.accounts.insert_one(doc)
    return res.inserted_id


async def get_available_account():
    return await db.accounts.find_one_and_update(
        {"status": "available"},
        {"$set": {"status": "assigned"}},
        sort=[("created_at", 1)],
    )


async def assign_account_to_user(account_id, user_id):
    await db.accounts.update_one(
        {"_id": ObjectId(account_id)},
        {"$set": {"assigned_to": int(user_id), "assigned_at": datetime.utcnow(), "status": "assigned"}},
    )


async def decrypt_cred(cipher_text: str) -> str:
    return fernet.decrypt(cipher_text.encode()).decode()


# Referrals
async def add_referral(referrer_id: int, referred_id: int):
    doc = {
        "referrer_id": int(referrer_id),
        "referred_id": int(referred_id),
        "joined_at": datetime.utcnow(),
        "left_at": None,
        "points_awarded": 10,
    }
    await db.referrals.insert_one(doc)
    await db.users.update_one({"user_id": int(referrer_id)}, {"$inc": {"points": 10}})


async def mark_referred_left(referred_id: int):
    r = await db.referrals.find_one({"referred_id": int(referred_id), "left_at": None})
    if r:
        await db.referrals.update_one({"_id": r["_id"]}, {"$set": {"left_at": datetime.utcnow()}})
        await db.users.update_one(
            {"user_id": int(r["referrer_id"])},
            {"$inc": {"points": -int(r.get("points_awarded", 10))}},
        )


# Proofs
async def save_proof(user_id: int, account_id: str, proof_type: str, file_id: str, posted_channel_id=None):
    doc = {
        "user_id": int(user_id),
        "account_id": account_id,
        "type": proof_type,
        "file_id": file_id,
        "posted_to_channel_id": posted_channel_id,
        "timestamp": datetime.utcnow(),
    }
    await db.proofs.insert_one(doc)


# Admin actions
async def log_admin_action(admin_id: int, action_type: str, target, meta=None):
    await db.admin_actions.insert_one(
        {
            "admin_id": int(admin_id),
            "action_type": action_type,
            "target": target,
            "meta": meta or {},
            "timestamp": datetime.utcnow(),
        }
    )
