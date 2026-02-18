import os
from aiogram import types
from db import db, add_account_doc, log_admin_action

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

async def is_admin(user_id: int) -> bool:
    return int(user_id) in ADMIN_IDS

# /admin_add_account name|credential|points|default
async def admin_add_account(message: types.Message, args: str):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ Not authorized.")
        return
    try:
        name, cred_plain, points_cost, default_flag = args.split("|")
        acc_id = await add_account_doc(name, cred_plain, int(points_cost), default_flag.strip().lower() == "default")
        await log_admin_action(message.from_user.id, "add_account", str(acc_id), {"name": name})
        await message.reply(f"✅ Account added: {acc_id}")
    except Exception as e:
        await message.reply(f"Error: {e}")

# /admin_gift_point userid|points|note
async def admin_gift_point(message: types.Message, args: str):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ Not authorized.")
        return
    try:
        uid, pts, note = args.split("|")
        uid = int(uid); pts = int(pts)
        await db.users.update_one({"user_id": uid}, {"$inc": {"points": pts}})
        await log_admin_action(message.from_user.id, "gift_point", uid, {"points": pts, "note": note})
        await message.reply("✅ Points updated.")
    except Exception as e:
        await message.reply(f"Error: {e}")

# /admin_ban userid
async def admin_ban(message: types.Message, args: str):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ Not authorized.")
        return
    try:
        uid = int(args.strip())
        await db.users.update_one({"user_id": uid}, {"$set": {"banned": True}})
        await log_admin_action(message.from_user.id, "ban", uid, {})
        await message.reply("✅ User banned.")
    except Exception as e:
        await message.reply(f"Error: {e}")

# /admin_unban userid
async def admin_unban(message: types.Message, args: str):
    if not await is_admin(message.from_user.id):
        await message.reply("❌ Not authorized.")
        return
    try:
        uid = int(args.strip())
        await db.users.update_one({"user_id": uid}, {"$set": {"banned": False}})
        await log_admin_action(message.from_user.id, "unban", uid, {})
        await message.reply("✅ User unbanned.")
    except Exception as e:
        await message.reply(f"Error: {e}")
