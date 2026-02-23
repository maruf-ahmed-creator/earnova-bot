from aiogram import types


def main_reply_keyboard(lang: str = "bn") -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("Get Account"))
    kb.add(types.KeyboardButton("Balance"), types.KeyboardButton("Referral"))
    kb.add(types.KeyboardButton("Bot Info"), types.KeyboardButton("Help"))
    kb.add(types.KeyboardButton("Total Users"))
    kb.add(types.KeyboardButton("Ask AI"), types.KeyboardButton("Language"))
    return kb


def verify_inline_kb(account_id: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ Working", callback_data=f"verify:working:{account_id}"),
        types.InlineKeyboardButton("❌ Not Working", callback_data=f"verify:notworking:{account_id}"),
    )
    return kb
