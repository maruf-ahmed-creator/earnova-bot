import os
from aiogram import types

from db import db, add_account_doc, log_admin_action

def _admin_ids():
    raw = os.getenv("ADMIN_IDS", "")
    ids = []
    for x in raw.replace(" ", "").split(","):
        if not x:
            continue
        try:
            ids.append(int(x))
        except Exception:
            pass
    return set(ids)


def _is_admin(user_id: int) -> bool:
    return int(user_id) in _admin_ids()


async def _deny_if_not_admin(message: types.Message) -> bool:
    if not _is_admin(message.from_user.id):
        await message.reply("❌ Admin only.")
        return True
    return False


async def admin_add_account(message: types.Message, args: str):
    if await _deny_if_not_admin(message):
        return

    # Usage: /admin_add_account account_name|credential|points_cost(optional)
    if not args or "|" not in args:
        await message.reply("Usage: /admin_add_account name|credential|points(optional)")
        return

    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 2:
        await message.reply("Usage: /admin_add_account name|credential|points(optional)")
        return

    name = parts[0]
    cred = parts[1]
    points = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 0

    _id = await add_account_doc(name, cred, points_cost=points)
    await log_admin_action(message.from_user.id, "add_account", str(_id), {"name": name, "points": points})
    await message.reply(f"✅ Added account: {name} (id={_id})")


async def admin_gift_point(message: types.Message, args: str):
    if await _deny_if_not_admin(message):
        return

    # Usage: /admin_gift_point user_id points
    if not args:
        await message.reply("Usage: /admin_gift_point user_id points")
        return

    parts = args.split()
    if len(parts) != 2:
        await message.reply("Usage: /admin_gift_point user_id points")
        return

    try:
        user_id = int(parts[0])
        pts = int(parts[1])
    except Exception:
        await message.reply("Usage: /admin_gift_point user_id points")
        return

    await db.users.update_one({"user_id": user_id}, {"$inc": {"points": pts}})
    await log_admin_action(message.from_user.id, "gift_points", user_id, {"points": pts})
    await message.reply(f"✅ Gifted {pts} points to {user_id}")


async def admin_ban(message: types.Message, args: str):
    if await _deny_if_not_admin(message):
        return

    # Usage: /admin_ban user_id
    if not args or not args.strip().isdigit():
        await message.reply("Usage: /admin_ban user_id")
        return

    user_id = int(args.strip())
    await db.users.update_one({"user_id": user_id}, {"$set": {"banned": True}})
    await log_admin_action(message.from_user.id, "ban", user_id, {})
    await message.reply(f"🚫 Banned user {user_id}")


async def admin_unban(message: types.Message, args: str):
    if await _deny_if_not_admin(message):
        return

    # Usage: /admin_unban user_id
    if not args or not args.strip().isdigit():
        await message.reply("Usage: /admin_unban user_id")
        return

    user_id = int(args.strip())
    await db.users.update_one({"user_id": user_id}, {"$set": {"banned": False}})
    await log_admin_action(message.from_user.id, "unban", user_id, {})
    await message.reply(f"✅ Unbanned user {user_id}")
