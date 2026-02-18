from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_reply_keyboard(lang="bn"):
    buttons = [
        ["Balance", "Referral"],
        ["Bot Info", "Help"],
        ["Ask AI", "Language"],
        ["Total Users", "Get Account"]
    ]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for row in buttons:
        kb.row(*[KeyboardButton(text=b) for b in row])
    return kb

def verify_inline_kb(account_obj_id: str):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Working", callback_data=f"verify:working:{account_obj_id}"))
    kb.add(InlineKeyboardButton("❌ Not Working", callback_data=f"verify:notworking:{account_obj_id}"))
    return kb
