from __future__ import annotations

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
    upsert_user, get_user, referral_counts, claim_resource_for_user, decrypt_secret,
    inc_accounts_taken, create_pending_proof, attach_proof_file, db, set_user_lang
)
from join_gate import check_user_joined, current_required_version
from rate_limit import allow
from ai import ask_ai

router = Router()

async def locked(bot: Bot, m: Message) -> bool:
    ok, missing, _ = await check_user_joined(bot, m.from_user.id)
    if not ok:
        await m.answer("⚠️ আগে আমাদের required চ্যানেলগুলোতে Join করো, তারপর /start দাও ✅\n" f"Missing channel id: {missing}")
        return True
    user = await get_user(m.from_user.id)
    v = await current_required_version()
    if user and int(user.get("joined_required_version", 0)) != int(v):
        await m.answer("🔒 নতুন চ্যানেল যুক্ত হয়েছে। সব required চ্যানেলে Join করে আবার /start দাও ✅")
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
        await m.answer("⚠️ আগে আমাদের চ্যানেলে Join করো, তারপর /start আবার দাও ✅")
        return

    v = await current_required_version()
    await db.users.update_one({"user_id": int(m.from_user.id)}, {"$set": {"joined_required_version": int(v)}})

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

    await m.answer("স্বাগতম! নিচের মেনু থেকে ব্যবহার করুন ✅", reply_markup=main_menu_kb())

@router.message(F.text == BTN_BALANCE)
async def balance(m: Message, bot: Bot):
    if await locked(bot, m):
        return
    user = await get_user(m.from_user.id)
    refs = await referral_counts(m.from_user.id)
    await m.answer(f"Points: {user.get('points', 0)}\nReferrals: {refs}\nAccounts taken: {user.get('accounts_taken', 0)}")

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
    await m.answer("Bot Status: Running ✅\n" f"Available accounts/resources: {avail}\n" f"Admins: {settings.ADMIN_IDS or '(not set)'}")

@router.message(F.text == BTN_HELP)
async def help_(m: Message, bot: Bot):
    if await locked(bot, m):
        return
    await m.answer(
        "📌 নিয়মকানুন / গাইড\n"
        "1) Required চ্যানেলগুলোতে Join\n"
        "2) Get Account চাপ\n"
        "3) Working/Not Working সিলেক্ট\n"
        "4) ১০ মিনিটের মধ্যে Screenshot পাঠা\n"
        "⚠️ না দিলে Auto-ban"
    )

@router.message(F.text == BTN_LANG)
async def language(m: Message, bot: Bot):
    if await locked(bot, m):
        return
    user = await get_user(m.from_user.id)
    cur = user.get("language", "bn") if user else "bn"
    new = "en" if cur == "bn" else "bn"
    await set_user_lang(m.from_user.id, new)
    await m.answer(f"Language set to: {new.upper()} ✅")

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
        await m.answer("❌ তুই ব্যান আছস।")
        return
    if int(user.get("points", 0)) < 0:
        await m.answer("❌ তোর পয়েন্ট মাইনাস। আগে পয়েন্ট earn কর, তারপর account নিতে পারবি।")
        return

    r = await claim_resource_for_user(m.from_user.id)
    if not r:
        await m.answer("এই মুহূর্তে কোনো অ্যাকাউন্ট available নাই 😔")
        return

    await inc_accounts_taken(m.from_user.id, 1)
    secret = decrypt_secret(r["secret"])
    sent = await m.answer(
        f"✅ Account/Resource: {r['name']}\n"
        f"Credential/Secret: {secret}\n\n"
        "⚠️ This message will auto-delete in 5 minutes."
    )

    deadline = datetime.utcnow() + timedelta(minutes=10)
    await create_pending_proof(m.from_user.id, str(r["_id"]), "pending", deadline)

    await m.answer("Verify কর:", reply_markup=verify_kb(str(r["_id"])))

    async def _del_later():
        import asyncio
        await asyncio.sleep(300)
        try:
            await sent.delete()
        except Exception:
            pass
    import asyncio
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

    p = await db.proofs.find_one({"user_id": int(cb.from_user.id), "status": "pending"}, sort=[("created_at", -1)])
    if not p:
        await cb.answer("No pending proof", show_alert=True)
        return
    await db.proofs.update_one({"_id": p["_id"]}, {"$set": {"type": status}})
    await cb.answer("✅ Verify done. ১০ মিনিটের মধ্যে Screenshot পাঠা!", show_alert=True)

@router.message(F.photo)
async def photo(m: Message, bot: Bot):
    if await locked(bot, m):
        return
    file_id = m.photo[-1].file_id
    proof = await attach_proof_file(m.from_user.id, file_id)
    if not proof:
        await m.answer("কোনো pending verification নাই")
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
    except Exception:
        pass

    if ptype == "notworking":
        try:
            await bot.send_photo(settings.PROOF_CHANNEL_DATA, file_id, caption=caption)
            posted.append(settings.PROOF_CHANNEL_DATA)
        except Exception:
            pass

    await db.proofs.update_one({"_id": proof["_id"]}, {"$set": {"posted": posted}})
    await m.answer("✅ Proof received. Thanks!")

@router.message(F.text == BTN_AI)
async def ai_mode(m: Message, bot: Bot):
    if await locked(bot, m):
        return
    await db.ai_state.update_one({"user_id": int(m.from_user.id)}, {"$set": {"until": datetime.utcnow().timestamp() + 60}}, upsert=True)
    await m.answer("AI mode on ✅ এখন প্রশ্ন লেখ। (60 seconds)")

@router.message(F.text)
async def any_text(m: Message, bot: Bot):
    st = await db.ai_state.find_one({"user_id": int(m.from_user.id)})
    if st and float(st.get("until", 0)) >= datetime.utcnow().timestamp():
        if await locked(bot, m):
            return
        user = await get_user(m.from_user.id)
        lang = user.get("language", "bn") if user else "bn"
        ans = await ask_ai(m.text, lang=lang)
        await db.ai_logs.insert_one({"user_id": int(m.from_user.id), "lang": lang, "q": m.text, "a": ans, "ts": datetime.utcnow()})
        await m.answer(ans)
        return

    if (m.text or "").strip() in {BTN_BALANCE, BTN_REFERRAL, BTN_INFO, BTN_HELP, BTN_AI, BTN_LANG, BTN_TOTAL, BTN_GET}:
        return
    await m.answer("মেনু থেকে বেছে নাও 🙂", reply_markup=main_menu_kb())
