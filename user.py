from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from config import settings
from keyboards import (
    main_menu_kb, verify_kb,
    BTN_BALANCE, BTN_REFERRAL, BTN_INFO, BTN_HELP, BTN_AI, BTN_LANG, BTN_TOTAL, BTN_GET
)
from db import (
    upsert_user, get_user, referral_counts, claim_resource_for_user, count_available_resources,
    decrypt_secret, inc_accounts_taken, create_pending_proof, attach_proof_file, db, set_user_lang
)
from join_gate import check_user_joined, current_required_version
from rate_limit import allow
from ai import ask_ai

log = logging.getLogger("earnova")

router = Router()


async def locked(bot: Bot, m: Message) -> bool:
    uid = m.from_user.id
    try:
        ok, missing, _ = await check_user_joined(bot, uid)
    except Exception as e:
        log.warning(f"locked() check_user_joined raised exception user={uid}: {e} — treating as OK")
        ok, missing = True, 0

    log.info(f"locked(): user={uid} channel_ok={ok} missing_channel={missing}")

    if not ok:
        await m.answer(
            "Please join our required channels first, then send /start\n"
            f"Missing: {missing}"
        )
        return True

    user = await get_user(uid)
    v = await current_required_version()
    user_ver = int(user.get("joined_required_version", 0)) if user else 0
    log.info(f"locked(): user={uid} user_ver={user_ver} required_ver={v}")

    if user and user_ver != int(v):
        await m.answer("New channel added. Please /start again to verify membership.")
        return True

    return False


@router.message(CommandStart())
async def start(m: Message, bot: Bot):
    if not allow(m.from_user.id, "start"):
        return

    args = (m.text or "").split(maxsplit=1)
    ref = None
    if len(args) == 2:
        try:
            ref = int(args[1])
        except Exception:
            ref = None
    if ref == m.from_user.id:
        ref = None

    await upsert_user(m.from_user.id, m.from_user.username, referrer_id=ref)

    ok, _, _ = await check_user_joined(bot, m.from_user.id)
    if not ok:
        await m.answer("Please join our channel first, then send /start again.")
        return

    v = await current_required_version()
    await db.users.update_one(
        {"user_id": int(m.from_user.id)},
        {"$set": {"joined_required_version": int(v)}}
    )

    if ref:
        existing = await db.referrals.find_one({"referred_id": int(m.from_user.id)})
        if not existing:
            await db.referrals.insert_one({
                "referrer_id": int(ref),
                "referred_id": int(m.from_user.id),
                "joined_at": datetime.utcnow(),
                "left_at": None,
                "points_awarded": 10,
            })
            await db.users.update_one({"user_id": int(ref)}, {"$inc": {"points": 10}})

    await m.answer("Welcome! Use the menu below.", reply_markup=main_menu_kb())


@router.message(F.text == BTN_BALANCE)
async def balance(m: Message, bot: Bot):
    if await locked(bot, m):
        return
    user = await get_user(m.from_user.id)
    refs = await referral_counts(m.from_user.id)
    pts = user.get("points", 0) if user else 0
    taken = user.get("accounts_taken", 0) if user else 0
    await m.answer(
        f"Points: {pts}\n"
        f"Referrals: {refs}\n"
        f"Accounts taken: {taken}"
    )


@router.message(F.text == BTN_REFERRAL)
async def referral(m: Message, bot: Bot):
    if await locked(bot, m):
        return
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={m.from_user.id}"
    await m.answer(f"Your referral link:\n{link}")


@router.message(F.text == BTN_INFO)
async def info(m: Message, bot: Bot):
    if await locked(bot, m):
        return
    avail = await db.resources.count_documents({"status": "available"})
    await m.answer(
        f"Bot Status: Running\n"
        f"Available accounts: {avail}"
    )


@router.message(F.text == BTN_HELP)
async def help_(m: Message, bot: Bot):
    if await locked(bot, m):
        return
    await m.answer(
        "Guide:\n"
        "1) Join all required channels\n"
        "2) Press Get Account\n"
        "3) Select Working or Not Working\n"
        "4) Send screenshot within 10 minutes\n"
        "WARNING: No screenshot = auto-ban"
    )


@router.message(F.text == BTN_LANG)
async def language(m: Message, bot: Bot):
    if await locked(bot, m):
        return
    user = await get_user(m.from_user.id)
    cur = user.get("language", "bn") if user else "bn"
    new = "en" if cur == "bn" else "bn"
    await set_user_lang(m.from_user.id, new)
    await m.answer(f"Language set to: {new.upper()}")


@router.message(F.text == BTN_TOTAL)
async def total_users(m: Message, bot: Bot):
    if await locked(bot, m):
        return
    total = await db.users.count_documents({})
    await m.answer(f"Total users: {total}")


@router.message(F.text == BTN_GET)
async def get_account(m: Message, bot: Bot):
    if await locked(bot, m):
        return

    user = await get_user(m.from_user.id)
    if not user:
        await start(m, bot)
        return
    if user.get("banned"):
        await m.answer("You are banned.")
        return
    if int(user.get("points", 0)) < 0:
        await m.answer("Your points are negative. Earn more points first.")
        return

    avail_before = await count_available_resources()
    log.info(f"get_account: user={m.from_user.id} available_before_claim={avail_before}")

    r = await claim_resource_for_user(m.from_user.id)

    if not r:
        avail_now = await count_available_resources()
        log.warning(f"get_account: claim returned None for user={m.from_user.id}, available_now={avail_now}")
        await m.answer(
            f"No accounts available right now.\n"
            f"(DB available: {avail_now})\n\n"
            "Run /res_reset if you are admin, or try again later."
        )
        return

    log.info(f"get_account: SUCCESS user={m.from_user.id} resource={r.get('_id')} name={r.get('name')}")
    await inc_accounts_taken(m.from_user.id, 1)
    secret = decrypt_secret(r["secret"])
    sent = await m.answer(
        f"Account: {r['name']}\n"
        f"Credentials: {secret}\n\n"
        "This message auto-deletes in 5 minutes."
    )

    deadline = datetime.utcnow() + timedelta(minutes=10)
    await create_pending_proof(m.from_user.id, str(r["_id"]), "pending", deadline)
    await m.answer("Please verify:", reply_markup=verify_kb(str(r["_id"])))

    async def _del_later():
        await asyncio.sleep(300)
        try:
            await sent.delete()
        except Exception:
            pass

    asyncio.create_task(_del_later())


@router.callback_query(F.data.startswith("verify:"))
async def verify(cb: CallbackQuery, bot: Bot):
    parts = (cb.data or "").split(":")
    if len(parts) != 3:
        await cb.answer("Invalid", show_alert=True)
        return
    _, status, _rid = parts
    if status not in ("working", "notworking"):
        await cb.answer("Invalid", show_alert=True)
        return

    p = await db.proofs.find_one(
        {"user_id": int(cb.from_user.id), "status": "pending"},
        sort=[("created_at", -1)]
    )
    if not p:
        await cb.answer("No pending proof found", show_alert=True)
        return
    await db.proofs.update_one({"_id": p["_id"]}, {"$set": {"type": status}})
    await cb.answer("Verified! Send screenshot within 10 minutes.", show_alert=True)


@router.message(F.photo)
async def photo(m: Message, bot: Bot):
    if await locked(bot, m):
        return
    file_id = m.photo[-1].file_id
    proof = await attach_proof_file(m.from_user.id, file_id)
    if not proof:
        await m.answer("No pending verification found.")
        return

    ptype = proof.get("type")
    rid = proof.get("resource_id")
    caption = (
        f"User: {m.from_user.id}\n"
        f"Resource: {rid}\n"
        f"Type: {ptype}\n"
        f"Time: {datetime.utcnow().isoformat()}"
    )

    posted = []
    try:
        await bot.send_photo(settings.PROOF_CHANNEL_PUBLIC, file_id, caption=caption)
        posted.append(settings.PROOF_CHANNEL_PUBLIC)
    except Exception as e:
        log.warning(f"Failed to send proof to PUBLIC channel: {e}")

    if ptype == "notworking":
        try:
            await bot.send_photo(settings.PROOF_CHANNEL_DATA, file_id, caption=caption)
            posted.append(settings.PROOF_CHANNEL_DATA)
        except Exception as e:
            log.warning(f"Failed to send proof to DATA channel: {e}")

    await db.proofs.update_one({"_id": proof["_id"]}, {"$set": {"posted": posted}})
    await m.answer("Proof received. Thank you!")


@router.message(F.text == BTN_AI)
async def ai_mode(m: Message, bot: Bot):
    if await locked(bot, m):
        return
    await db.ai_state.update_one(
        {"user_id": int(m.from_user.id)},
        {"$set": {"until": datetime.utcnow().timestamp() + 60}},
        upsert=True
    )
    await m.answer("AI mode on. Ask your question now. (60 seconds)")


@router.message(F.text)
async def any_text(m: Message, bot: Bot):
    st = await db.ai_state.find_one({"user_id": int(m.from_user.id)})
    if st and float(st.get("until", 0)) >= datetime.utcnow().timestamp():
        if await locked(bot, m):
            return
        user = await get_user(m.from_user.id)
        lang = user.get("language", "bn") if user else "bn"
        ans = await ask_ai(m.text, lang=lang)
        await db.ai_logs.insert_one({
            "user_id": int(m.from_user.id),
            "lang": lang,
            "q": m.text,
            "a": ans,
            "ts": datetime.utcnow()
        })
        await m.answer(ans, parse_mode=None)
        return

    if (m.text or "").strip() in {BTN_BALANCE, BTN_REFERRAL, BTN_INFO, BTN_HELP, BTN_AI, BTN_LANG, BTN_TOTAL, BTN_GET}:
        return
    await m.answer("Please use the menu buttons.", reply_markup=main_menu_kb())
