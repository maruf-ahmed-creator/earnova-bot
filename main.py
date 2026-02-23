import os
import logging
import asyncio

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv

from handlers import (
    start_handler,
    text_handler,
    callback_query_handler,
    photo_handler,
)
from admin import (
    admin_add_account,
    admin_gift_point,
    admin_ban,
    admin_unban,
)
from tasks import referral_leave_watcher

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing in environment variables")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await start_handler(message)


@dp.message_handler(commands=["admin_add_account"])
async def cmd_admin_add_account(message: types.Message):
    await admin_add_account(message, message.get_args())


@dp.message_handler(commands=["admin_gift_point"])
async def cmd_admin_gift_point(message: types.Message):
    await admin_gift_point(message, message.get_args())


@dp.message_handler(commands=["admin_ban"])
async def cmd_admin_ban(message: types.Message):
    await admin_ban(message, message.get_args())


@dp.message_handler(commands=["admin_unban"])
async def cmd_admin_unban(message: types.Message):
    await admin_unban(message, message.get_args())


@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    await photo_handler(message)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("verify:"))
async def handle_callback(c: types.CallbackQuery):
    await callback_query_handler(c)


@dp.message_handler()
async def all_text(message: types.Message):
    await text_handler(message)


async def on_startup(_dp: Dispatcher):
    asyncio.create_task(referral_leave_watcher(bot))
    logging.info("✅ Background tasks started.")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
