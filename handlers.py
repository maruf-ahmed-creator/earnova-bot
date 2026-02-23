import os
import asyncio
from datetime import datetime

from aiogram import types

from db import (
    db,
    get_user,
    create_user_doc,
    get_available_account,
    decrypt_cred,
    add_referral,
    assign_account_to_user,
)
from utils import main_reply_keyboard, verify_inline_kb

def _env_int(name: str) -> int:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} missing in environment variables")
    return int(v)

MAIN_CHANNEL_ID = _env_int("MAIN_CHANNEL_ID")
EARNOVA_CHANNEL_ID = _env_int("EARNOVA_CHANNEL_ID")
DATA_CHANNEL_ID = _env_int("DATA_CHANNEL_ID")


# -------- START (/start) --------
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()

    # referral handling
    referrer_id = None
    if args:
        try:
            referrer_id = int(args)
        except Exception:
            referrer_id = None

    # block self-referral
    if referrer_id == user_id:
        referrer_id = None

    await create_user_doc(user_id, message.from_user.username, referrer_id)

    # award referral only if user is new (avoid duplicates)
    if referrer_id:
        already = await db.referrals.find_one({"referred_id": user_id})
        if not already:
            await add_referral(referrer_id, user_id)

    # check join
    try:
        member = await message.bot.get_chat_member(MAIN_CHANNEL_ID, user_id)
        if member.status in ["left", "kicked"]:
            raise RuntimeError("not joined")

        user = await get_user(user_id)
        kb = main_reply_keyboard(lang=user.get("language", "bn"))
        await message.reply("স্বাগতম! নিচের মেনু থেকে ব্যবহার করুন ✅", reply_markup=kb)

    except Exception:
        chat = await message.bot.get_chat(MAIN_CHANNEL_ID)
        join_link = f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{str(MAIN_CHANNEL_ID)[4:]}"
        await message.reply(
            f"⚠️ আগে আমাদের MAIN চ্যানেলে জয়েন করতে হবে:\n{join_link}\n\nতারপর /start আবার চাপবি ✅"
        )


# -------- TEXT MENU --------
async def text_handler(message: types.Message):
    text = (message.text or "").strip()
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user:
        await start_handler(message)
        return

    # ensure joined
    try:
        member = await message.bot.get_chat_member(MAIN_CHANNEL_ID, user_id)
        if member.status in ["left", "kicked"]:
            await message.reply("তুই MAIN চ্যানেলে জয়েন করিস নাই। আগে জয়েন কর ✅")
            return
    except Exception:
        await message.reply("তুই MAIN চ্যানেলে জয়েন করিস নাই। আগে জয়েন কর ✅")
        return

    if text == "Balance":
        referrals_count = await db.referrals.count_documents({"referrer_id": user_id})
        await message.reply(
            f"Points: {user.get('points', 0)}\n"
            f"Referrals: {referrals_count}\n"
            f"Accounts taken: {len(user.get('accounts_taken', []))}"
        )

    elif text == "Referral":
        me = await message.bot.get_me()
        link = f"https://t.me/{me.username}?start={user_id}"
        await message.reply(f"Your referral link:\n{link}")

    elif text == "Bot Info":
        total_accounts = await db.accounts.count_documents({"status": "available"})
        admins = os.getenv("ADMIN_IDS", "")
        await message.reply(f"Bot Status: Running ✅\nAvailable accounts: {total_accounts}\nAdmins: {admins}")

    elif text == "Help":
        await message.reply(
            "বট ব্যবহার:\n"
            "1) MAIN চ্যানেলে জয়েন\n"
            "2) Get Account\n"
            "3) Working/Not Working চাপ\n"
            "4) ১০ মিনিটের মধ্যে Screenshot দিবি\n\n"
            "⚠️ না দিলে Auto-ban"
        )

    elif text == "Ask AI":
        await message.reply("AI ফিচার এখন placeholder (চাইলে পরে add করবো)")

    elif text == "Language":
        await message.reply("ভাষা change এখন placeholder")

    elif text == "Total Users":
        total = await db.users.count_documents({})
        await message.reply(f"Total users: {total}")

    elif text == "Get Account":
        if user.get("banned"):
            await message.reply("❌ তুই ব্যান আছস।")
            return

        acc = await get_available_account()
        if not acc:
            await message.reply("এই মুহূর্তে কোনো অ্যাকাউন্ট available নাই")
            return

        # IMPORTANT: Only distribute credentials you own / have permission to share.
        await assign_account_to_user(acc["_id"], user_id)
        cred = await decrypt_cred(acc["credential"])

        sent = await message.reply(
            f"✅ Account: {acc['account_name']}\n"
            f"Credential: {cred}\n\n"
            "⚠️ This message will delete in 5 minutes."
        )

        await message.reply("এখন verify কর:", reply_markup=verify_inline_kb(str(acc["_id"])))

        async def delete_later(msg: types.Message):
            await asyncio.sleep(300)
            try:
                await msg.delete()
            except Exception:
                pass

        asyncio.create_task(delete_later(sent))

    else:
        await message.reply("এইটা বুঝলাম না। মেনু থেকে বেছে নে।")


# -------- VERIFY CALLBACK --------
async def callback_query_handler(callback: types.CallbackQuery):
    data = callback.data or ""
    parts = data.split(":")
    if len(parts) != 3:
        await callback.answer("Invalid", show_alert=True)
        return

    _, status, acc_id = parts
    if status not in ("working", "notworking"):
        await callback.answer("Invalid", show_alert=True)
        return

    user_id = callback.from_user.id

    # create proof record pending screenshot
    await db.proofs.insert_one(
        {
            "user_id": user_id,
            "account_id": acc_id,
            "type": status,
            "file_id": None,
            "posted_to_channel_id": None,
            "timestamp": datetime.utcnow(),
        }
    )

    await callback.answer("✅ Verify done. ১০ মিনিটের মধ্যে Screenshot পাঠা!", show_alert=True)

    # auto-ban if no screenshot
    async def wait_for_screenshot():
        await asyncio.sleep(600)
        p = await db.proofs.find_one(
            {"user_id": user_id, "account_id": acc_id, "file_id": {"$ne": None}}
        )
        if not p:
            await db.users.update_one({"user_id": user_id}, {"$set": {"banned": True}})
            try:
                await callback.bot.send_message(
                    EARNOVA_CHANNEL_ID,
                    f"Auto-ban: User {user_id} did not submit screenshot for account {acc_id}",
                )
            except Exception:
                pass

    asyncio.create_task(wait_for_screenshot())


# -------- PHOTO / SCREENSHOT --------
async def photo_handler(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        await message.reply("প্রথমে /start কর ✅")
        return

    proof = await db.proofs.find_one({"user_id": user_id, "file_id": None}, sort=[("timestamp", -1)])
    if not proof:
        await message.reply("কোনো pending verification নাই")
        return

    file_id = message.photo[-1].file_id
    await db.proofs.update_one({"_id": proof["_id"]}, {"$set": {"file_id": file_id}})

    ptype = proof.get("type")
    acc_id = proof.get("account_id")
    caption = (
        f"User: {user_id}\n"
        f"Account: {acc_id}\n"
        f"Type: {ptype}\n"
        f"Time: {datetime.utcnow().isoformat()}"
    )

    if ptype == "working":
        try:
            await message.bot.send_photo(EARNOVA_CHANNEL_ID, file_id, caption=caption)
            await db.proofs.update_one({"_id": proof["_id"]}, {"$set": {"posted_to_channel_id": EARNOVA_CHANNEL_ID}})
        except Exception:
            pass
    else:
        try:
            await message.bot.send_photo(DATA_CHANNEL_ID, file_id, caption=caption)
            await db.proofs.update_one({"_id": proof["_id"]}, {"$set": {"posted_to_channel_id": DATA_CHANNEL_ID}})
        except Exception:
            pass

    await message.reply("✅ Proof received. Thanks!")
