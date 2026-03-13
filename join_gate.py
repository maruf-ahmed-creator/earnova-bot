from __future__ import annotations

import time
import logging
from typing import Tuple, List, Dict
from aiogram import Bot

from config import settings
from db import list_channels, get_required_version

log = logging.getLogger("earnova")

# In-memory cache: {user_id: (is_ok, missing_cid, expires_at)}
_membership_cache: Dict[int, Tuple[bool, int, float]] = {}
_CACHE_TTL = 60  # seconds — re-check channel membership every 60s


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
    now = time.monotonic()
    cached = _membership_cache.get(user_id)
    req = await required_channels()

    if cached and now < cached[2]:
        ok, missing = cached[0], cached[1]
        log.debug(f"check_user_joined: CACHE HIT user={user_id} ok={ok}")
        return ok, missing, req

    for cid in req:
        try:
            m = await bot.get_chat_member(cid, user_id)
            if m.status in ("left", "kicked"):
                _membership_cache[user_id] = (False, cid, now + _CACHE_TTL)
                log.info(f"check_user_joined: user={user_id} NOT in channel={cid}")
                return False, cid, req
        except Exception as e:
            log.warning(f"check_user_joined: get_chat_member failed cid={cid} user={user_id}: {e} — treating as OK")
            # If the bot cannot check (e.g. not admin in channel), do NOT lock the user out
            continue

    _membership_cache[user_id] = (True, 0, now + _CACHE_TTL)
    return True, 0, req


def invalidate_membership_cache(user_id: int):
    """Call this after /start to force a fresh membership check."""
    _membership_cache.pop(user_id, None)


async def current_required_version() -> int:
    return await get_required_version()
