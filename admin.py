from __future__ import annotations

from datetime import datetime
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode

from config import settings
from db import (
    add_channel, remove_channel, list_channels,
    inc_points, set_banned,
    add_resource, remove_resource, list_resources,
    db
)

router = Router()

def is_admin(user_id: int) -> bool:
    return int(user_id) in settings.admin_id_set()

async def deny(m: Message) -> bool:
    if not is_admin(m.from_user.id):
        await m.reply("❌ Admin only.", parse_mode=None)
        return True
    return False

@router.message(Command("admin"))
async def admin_help(m: Message):
    if await deny(m):
        return
    await m.answer(
        "🛠 Admin Commands\n"
        "/ch_add [channel_id] required\n"
        "/ch_remove [channel_id]\n"
        "/ch_list\n"
        "/points_give [user_id] [points] [note]\n"
        "/points_take [user_id] [points] [note]\n"
        "/ban [user_id]\n"
        "/unban [user_id]\n"
        "/res_add [name]|[secret]|[cost]|[default_flag 0/1]\n"
        "/res_remove [resource_id]\n"
        "/res_list\n"
        "/broadcast [text]\n"
        "/stats",
        parse_mode=None,
    )

@router.message(Command("ch_add"))
async def ch_add(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await m.reply("Usage: /ch_add [channel_id] required", parse_mode=None)
        return
    try:
        cid = int(parts[1])
    except Exception:
        await m.reply("Invalid channel_id", parse_mode=None)
        return
    ch_type = parts[2].strip()
    if ch_type not in ("required",):
        await m.reply("Only supported type: required", parse_mode=None)
        return
    await add_channel(cid, ch_type)
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "ch_add", "payload": {"cid": cid, "type": ch_type}, "ts": datetime.utcnow()})
    await m.reply("✅ Channel added.", parse_mode=None)

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
    except Exception:
        await m.reply("Invalid channel_id", parse_mode=None)
        return
    await remove_channel(cid)
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "ch_remove", "payload": {"cid": cid}, "ts": datetime.utcnow()})
    await m.reply("✅ Channel removed.", parse_mode=None)

@router.message(Command("ch_list"))
async def ch_list(m: Message):
    if await deny(m):
        return
    chs = await list_channels()
    if not chs:
        await m.reply("No extra channels in DB.", parse_mode=None)
        return
    lines = [f"- {c['channel_id']} ({c.get('type')})" for c in chs]
    await m.reply("Channels:\n" + "\n".join(lines), parse_mode=None)

@router.message(Command("points_give"))
async def points_give(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=3)
    if len(parts) < 3:
        await m.reply("Usage: /points_give [user_id] [points] [note]", parse_mode=None)
        return
    try:
        uid = int(parts[1]); pts = int(parts[2])
    except Exception:
        await m.reply("Invalid numbers", parse_mode=None)
        return
    await inc_points(uid, pts)
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "points_give", "payload": {"uid": uid, "pts": pts, "note": parts[3] if len(parts) == 4 else ""}, "ts": datetime.utcnow()})
    await m.reply(f"✅ Gave {pts} points to {uid}", parse_mode=None)

@router.message(Command("points_take"))
async def points_take(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=3)
    if len(parts) < 3:
        await m.reply("Usage: /points_take [user_id] [points] [note]", parse_mode=None)
        return
    try:
        uid = int(parts[1]); pts = int(parts[2])
    except Exception:
        await m.reply("Invalid numbers", parse_mode=None)
        return
    await inc_points(uid, -abs(pts))
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "points_take", "payload": {"uid": uid, "pts": pts, "note": parts[3] if len(parts) == 4 else ""}, "ts": datetime.utcnow()})
    await m.reply(f"✅ Took {pts} points from {uid}", parse_mode=None)

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
    except Exception:
        await m.reply("Invalid user_id", parse_mode=None)
        return
    await set_banned(uid, True)
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "ban", "payload": {"uid": uid}, "ts": datetime.utcnow()})
    await m.reply(f"🚫 Banned {uid}", parse_mode=None)

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
    except Exception:
        await m.reply("Invalid user_id", parse_mode=None)
        return
    await set_banned(uid, False)
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "unban", "payload": {"uid": uid}, "ts": datetime.utcnow()})
    await m.reply(f"✅ Unbanned {uid}", parse_mode=None)

@router.message(Command("res_add"))
async def res_add(m: Message):
    if await deny(m):
        return
    args = (m.text or "").split(maxsplit=1)
    if len(args) != 2 or "|" not in args[1]:
        await m.reply("Usage: /res_add [name]|[secret]|[cost]|[default_flag 0/1]", parse_mode=None)
        return
    parts = [p.strip() for p in args[1].split("|")]
    if len(parts) < 2:
        await m.reply("Usage: /res_add [name]|[secret]|[cost]|[default_flag 0/1]", parse_mode=None)
        return
    name = parts[0]
    secret = parts[1]
    cost = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 0
    default_flag = bool(int(parts[3])) if len(parts) >= 4 and parts[3].isdigit() else False
    rid = await add_resource(name, secret, cost=cost, default_flag=default_flag)
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "res_add", "payload": {"rid": str(rid), "name": name}, "ts": datetime.utcnow()})
    await m.reply(f"✅ Resource added: {name}\nID: {rid}", parse_mode=None)

@router.message(Command("res_remove"))
async def res_remove(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await m.reply("Usage: /res_remove [resource_id]", parse_mode=None)
        return
    ok = await remove_resource(parts[1].strip())
    await db.admin_actions.insert_one({"admin_id": int(m.from_user.id), "action": "res_remove", "payload": {"rid": parts[1].strip(), "ok": ok}, "ts": datetime.utcnow()})
    await m.reply("✅ Removed" if ok else "❌ Invalid ID", parse_mode=None)

@router.message(Command("res_list"))
async def res_list(m: Message):
    if await deny(m):
        return
    rs = await list_resources(30)
    if not rs:
        await m.reply("No resources found.", parse_mode=None)
        return
    lines = [f"- {r['_id']} | {r['name']} | {r['status']}" for r in rs]
    await m.reply("Resources (latest 30):\n" + "\n".join(lines), parse_mode=None)

@router.message(Command("broadcast"))
async def broadcast(m: Message):
    if await deny(m):
        return
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[1].strip():
        await m.reply("Usage: /broadcast [text]", parse_mode=None)
        return
    text = parts[1].strip()
    await db.broadcast_jobs.insert_one({"text": text, "created_at": datetime.utcnow(), "status": "queued", "sent": 0, "failed": 0})
    await m.reply("✅ Broadcast queued.", parse_mode=None)

@router.message(Command("stats"))
async def stats(m: Message):
    if await deny(m):
        return
    users = await db.users.count_documents({})
    avail = await db.resources.count_documents({"status": "available"})
    assigned = await db.resources.count_documents({"status": "assigned"})
    pending = await db.proofs.count_documents({"status": "pending"})
    await m.reply(
        f"Users: {users}\nAvailable: {avail}\nAssigned: {assigned}\nPending proofs: {pending}",
        parse_mode=None,
    )
