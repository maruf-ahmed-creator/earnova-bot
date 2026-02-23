from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

BTN_BALANCE = "Balance"
BTN_REFERRAL = "Referral"
BTN_INFO = "Bot Info"
BTN_HELP = "Help"
BTN_AI = "Ask AI"
BTN_LANG = "Language"
BTN_TOTAL = "Total Users"
BTN_GET = "Get Account"

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BALANCE), KeyboardButton(text=BTN_REFERRAL)],
            [KeyboardButton(text=BTN_INFO), KeyboardButton(text=BTN_HELP)],
            [KeyboardButton(text=BTN_AI), KeyboardButton(text=BTN_LANG)],
            [KeyboardButton(text=BTN_TOTAL), KeyboardButton(text=BTN_GET)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

def verify_kb(resource_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Working", callback_data=f"verify:working:{resource_id}"),
        InlineKeyboardButton(text="❌ Not Working", callback_data=f"verify:notworking:{resource_id}"),
    ]])
