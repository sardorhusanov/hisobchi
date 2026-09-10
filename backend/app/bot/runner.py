import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
router = Router()


@router.message(CommandStart())
async def start(message: Message) -> None:
    settings = get_settings()
    role = "SUPER_ADMIN" if message.from_user and message.from_user.id == settings.super_admin_telegram_id else "foydalanuvchi"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Mini Appni ochish", web_app=WebAppInfo(url="http://localhost:5173"))]]
    )
    await message.answer(f"Assalomu alaykum! Sizning rolingiz: {role}.", reply_markup=keyboard)


async def main() -> None:
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required to run the bot")
    bot = Bot(settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
