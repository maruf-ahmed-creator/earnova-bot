from __future__ import annotations

import logging
from datetime import datetime, timezone
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from config import settings
from db import (
    add_channel, remove_channel, list_channels,
    inc_points, set_banned,
    add_resource, remove_resource, list_resources,
    reset_all_stuck_resources,
    get_user, db
)

log = logging.getLogger("earnova")
router = Router()


def is_admin(user_id: int) -> bool:
    return int(user_id) in settings.admin_id_set()


async def deny(m: Message) -> bool:
    if not is_admin(m.from_user.id):
        await m.reply("❌ Admin only.", parse_mode=None)
        return True
    return False


# ─── HELP ──────────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_help(m: Message):
    if await deny(m):
        return
    await m.answer(
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🛠 ADMIN COMMANDS\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 STATS\n"
        "/stats — bot statistics\n"
        "/res_list — list all accounts\n"
        "/ch_list — list required channels\n\n"
        "👤 USER MANAGEMENT\n"
        "/user_info [user_id] — inspect user\n"
        "/ban [user_id] — ban user\n"
        "/unban [user_id] — unban user\n"
        "/points_give [user_id] [pts] — add points\n"
        "/points_take [user_id] [pts] — remove points\n"
        "/msg [user_id] [text] — DM a user\n\n"
        "🔍 DEBUG\n"
        "/debug_db — raw DB dump of all accounts\n\n"
        "📦 ACCOUNT MANAGEMENT\n"
        "/res_add [name] | [secret] — add account\n"
        "  (optional: | [cost] | [1 if default])\n"
        "/res_remove [id] — delete account\n"
        "/res_reset — free all stuck accounts\n\n"
        "📢 CHANNELS\n"
        "/ch_add [channel_id] required — add channel\n"
        "/ch_remove [channel_id] — remove channel\n\n"
        "📣 BROADCAST\n"
        "/broadcast [text] — send to all users\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        parse_mode=None,
    )


# ─── STATS ─────────────────────────────────────────────────────────────────────

@router.message(Command("stats"))
async def stats(m: Message):
    if await deny(m):
        return
    users = await db.users.count_documents({})
    banned = await db.users.count_documents({"banned": True})
    avail = await db.resources.count_documents({"status": "available"})
    assigned = await db.resources.count_documents({"status": "assigned"})
    total_res = await db.resources.count_documents({})
    channels = await db.channels.count_documents({})
    pending = await db.proofs.count_documents({"status": "pending"})
    ai_chats = await db.ai_logs.count_documents({})

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    new_today = await db.users.count_documents({"created_at": {"$gte": today_start}})

    await m.reply(
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 BOT STATS\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total users: {users}\n"
        f"🚫 Banned users: {banned}\n"
        f"🆕 New today: {new_today}\n\n"
        f"📦 Accounts total: {total_res}\n"
        f"  ✅ Available: {avail}\n"
        f"  🔒 Assigned: {assigned}\n\n"
        f"📢 Required channels: {channels + 1}\n"
        f"⏳ Pending proofs: {pending}\n"
        f"🤖 AI chats logged: {ai_chats}\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        parse_mode=None,
    )


# ─── USER MANAGEMENT ───────────────────────────────────────────────────────────

@router.message(Command("user_info"))
async def user_info(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await m.reply("Usage: /user_info [user_id]", parse_mode=None)
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await m.reply("Invalid user_id", parse_mode=None)
        return
    u = await get_user(uid)
    if not u:
        await m.reply(f"User {uid} not found.", parse_mode=None)
        return
    await m.reply(
        f"👤 User: {uid}\n"
        f"Username: @{u.get('username', 'N/A')}\n"
        f"Points: {u.get('points', 0)}\n"
        f"Referrals: {u.get('referral_count', 0)}\n"
        f"Accounts taken: {u.get('accounts_taken', 0)}\n"
        f"Language: {u.get('language', 'bn')}\n"
        f"Banned: {u.get('banned', False)}\n"
        f"Joined version: {u.get('joined_required_version', 0)}\n"
        f"Created: {u.get('created_at', 'N/A')}",
        parse_mode=None,
    )


@router.message(Command("ban"))
async def ban(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await m.reply("Usage: /ban [user_id]", parse_mode=None)
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await m.reply("Invalid user_id", parse_mode=None)
        return
    await set_banned(uid, True)
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "ban", "payload": {"uid": uid}, "ts": datetime.utcnow()})
    await m.reply(f"🚫 Banned user {uid}", parse_mode=None)


@router.message(Command("unban"))
async def unban(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await m.reply("Usage: /unban [user_id]", parse_mode=None)
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await m.reply("Invalid user_id", parse_mode=None)
        return
    await set_banned(uid, False)
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "unban", "payload": {"uid": uid}, "ts": datetime.utcnow()})
    await m.reply(f"✅ Unbanned user {uid}", parse_mode=None)


@router.message(Command("points_give"))
async def points_give(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=3)
    if len(parts) < 3:
        await m.reply("Usage: /points_give [user_id] [points]", parse_mode=None)
        return
    try:
        uid = int(parts[1])
        pts = int(parts[2])
    except ValueError:
        await m.reply("Invalid numbers", parse_mode=None)
        return
    await inc_points(uid, pts)
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "points_give", "payload": {"uid": uid, "pts": pts}, "ts": datetime.utcnow()})
    await m.reply(f"✅ Gave {pts} points to user {uid}", parse_mode=None)


@router.message(Command("points_take"))
async def points_take(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=3)
    if len(parts) < 3:
        await m.reply("Usage: /points_take [user_id] [points]", parse_mode=None)
        return
    try:
        uid = int(parts[1])
        pts = int(parts[2])
    except ValueError:
        await m.reply("Invalid numbers", parse_mode=None)
        return
    await inc_points(uid, -abs(pts))
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "points_take", "payload": {"uid": uid, "pts": pts}, "ts": datetime.utcnow()})
    await m.reply(f"✅ Took {pts} points from user {uid}", parse_mode=None)


@router.message(Command("msg"))
async def msg_user(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await m.reply("Usage: /msg [user_id] [text]", parse_mode=None)
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await m.reply("Invalid user_id", parse_mode=None)
        return
    text = parts[2]
    try:
        await m.bot.send_message(uid, f"📩 Message from admin:\n\n{text}", parse_mode=None)
        await m.reply(f"✅ Message sent to {uid}", parse_mode=None)
    except Exception as e:
        await m.reply(f"❌ Failed to send: {e}", parse_mode=None)


# ─── ACCOUNT MANAGEMENT ────────────────────────────────────────────────────────

@router.message(Command("debug_db"))
async def debug_db(m: Message):
    if await deny(m):
        return
    total = await db.resources.count_documents({})
    avail = await db.resources.count_documents({"status": "available"})
    assigned = await db.resources.count_documents({"status": "assigned"})
    other = total - avail - assigned

    lines = [f"DB DUMP — resources (total={total})\navailable={avail} assigned={assigned} other={other}\n"]
    cursor = db.resources.find({}).sort("created_at", -1).limit(10)
    async for r in cursor:
        lines.append(
            f"ID: {r['_id']}\n"
            f"  Name: {r.get('name')}\n"
            f"  Status: {r.get('status')}\n"
            f"  AssignedTo: {r.get('assigned_to')}\n"
            f"  Cost: {r.get('cost')}\n"
            f"  Default: {r.get('default_flag')}"
        )
    await m.reply("\n\n".join(lines), parse_mode=None)


@router.message(Command("res_add"))
async def res_add(m: Message):
    if await deny(m):
        return
    args = (m.text or "").split(maxsplit=1)
    if len(args) != 2 or "|" not in args[1]:
        await m.reply(
            "Usage: /res_add [name] | [secret]\n"
            "Optional: /res_add [name] | [secret] | [cost] | [1 if default, 0 otherwise]\n\n"
            "Example: /res_add Netflix | user@email.com:pass123\n"
            "Example: /res_add Netflix | user@email.com:pass123 | 10 | 1",
            parse_mode=None,
        )
        return
    parts = [p.strip() for p in args[1].split("|")]
    if len(parts) < 2 or not parts[0] or not parts[1]:
        await m.reply("Name and secret are required.\nFormat: /res_add [name] | [secret]", parse_mode=None)
        return
    name = parts[0]
    secret = parts[1]
    cost = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 0
    default_flag = bool(int(parts[3])) if len(parts) >= 4 and parts[3].isdigit() else False
    rid = await add_resource(name, secret, cost=cost, default_flag=default_flag)
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "res_add", "payload": {"rid": str(rid), "name": name}, "ts": datetime.utcnow()})
    await m.reply(
        f"✅ Account added!\nName: {name}\nCost: {cost} pts\nDefault: {default_flag}\nID: {rid}",
        parse_mode=None,
    )


@router.message(Command("res_remove"))
async def res_remove(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await m.reply("Usage: /res_remove [account_id]\n(Copy ID from /res_list)", parse_mode=None)
        return
    ok = await remove_resource(parts[1].strip())
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "res_remove", "payload": {"rid": parts[1].strip(), "ok": ok}, "ts": datetime.utcnow()})
    await m.reply("✅ Account removed" if ok else "❌ Invalid ID — check /res_list for correct ID", parse_mode=None)


@router.message(Command("res_list"))
async def res_list(m: Message):
    if await deny(m):
        return
    rs = await list_resources(30)
    avail = await db.resources.count_documents({"status": "available"})
    assigned = await db.resources.count_documents({"status": "assigned"})
    if not rs:
        await m.reply("No accounts in database.\nAdd one with /res_add", parse_mode=None)
        return
    lines = [f"{'✅' if r['status'] == 'available' else '🔒'} {r['name']} [{r['status']}]\nID: {r['_id']}" for r in rs]
    header = f"📦 Accounts ({avail} available, {assigned} assigned)\n━━━━━━━━━━━━\n"
    await m.reply(header + "\n\n".join(lines), parse_mode=None)


@router.message(Command("res_reset"))
async def res_reset(m: Message):
    if await deny(m):
        return
    count = await reset_all_stuck_resources()
    await m.reply(
        f"✅ Reset complete.\n{count} assigned account(s) freed back to available.\n\nCheck /res_list to verify.",
        parse_mode=None,
    )


# ─── CHANNELS ──────────────────────────────────────────────────────────────────

@router.message(Command("ch_add"))
async def ch_add(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await m.reply(
            "Usage: /ch_add [channel_id] required\n\n"
            "Example: /ch_add -1001234567890 required\n"
            "Note: channel_id must start with -100",
            parse_mode=None,
        )
        return
    try:
        cid = int(parts[1])
    except ValueError:
        await m.reply("Invalid channel_id. Must be a number like -1001234567890", parse_mode=None)
        return
    ch_type = parts[2].strip()
    if ch_type != "required":
        await m.reply("Only supported type: required", parse_mode=None)
        return
    await add_channel(cid, ch_type)
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "ch_add", "payload": {"cid": cid, "type": ch_type}, "ts": datetime.utcnow()})
    await m.reply(f"✅ Channel {cid} added as required.\nAll users must now join it to use the bot.", parse_mode=None)


@router.message(Command("ch_remove"))
async def ch_remove(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await m.reply("Usage: /ch_remove [channel_id]", parse_mode=None)
        return
    try:
        cid = int(parts[1])
    except ValueError:
        await m.reply("Invalid channel_id", parse_mode=None)
        return
    await remove_channel(cid)
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "ch_remove", "payload": {"cid": cid}, "ts": datetime.utcnow()})
    await m.reply(f"✅ Channel {cid} removed.", parse_mode=None)


@router.message(Command("ch_list"))
async def ch_list(m: Message):
    if await deny(m):
        return
    chs = await list_channels()
    lines = [f"• {settings.REQUIRED_CHANNEL_ID} (main — from config)"]
    for c in chs:
        lines.append(f"• {c['channel_id']} ({c.get('type', 'required')})")
    await m.reply("📢 Required Channels:\n" + "\n".join(lines), parse_mode=None)


# ─── BROADCAST ─────────────────────────────────────────────────────────────────

@router.message(Command("broadcast"))
async def broadcast(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[1].strip():
        await m.reply("Usage: /broadcast [text]\n\nExample: /broadcast Hello everyone!", parse_mode=None)
        return
    text = parts[1].strip()
    user_count = await db.users.count_documents({})
    await db.broadcast_jobs.insert_one({"text": text, "created_at": datetime.utcnow(), "status": "queued", "sent": 0, "failed": 0})
    await m.reply(f"✅ Broadcast queued for {user_count} users.\nIt will be sent gradually to avoid Telegram limits.", parse_mode=None)
