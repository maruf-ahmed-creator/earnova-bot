from __future__ import annotations
from typing import Tuple, List
from aiogram import Bot

from config import settings
from db import list_channels, get_required_version

async def required_channels() -> List[int]:
    chs = await list_channels()
    req = [settings.REQUIRED_CHANNEL_ID]
    for c in chs:
        if c.get("type") == "required":
            cid = int(c["channel_id"])
            if cid not in req:
                req.append(cid)
    return req

async def check_user_joined(bot: Bot, user_id: int) -> Tuple[bool, int, List[int]]:
    req = await required_channels()
    for cid in req:
        try:
            m = await bot.get_chat_member(cid, user_id)
            if m.status in ("left", "kicked"):
                return False, cid, req
        except Exception:
            return False, cid, req
    return True, 0, req

async def current_required_version() -> int:
    return await get_required_version()
