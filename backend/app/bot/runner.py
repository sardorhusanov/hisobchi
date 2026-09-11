import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.members import MemberService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
router = Router()


@router.message(CommandStart())
async def start(message: Message) -> None:
    settings = get_settings()
    if message.from_user is None:
        return
    async with SessionFactory() as session:
        user = await MemberService(session).user_by_telegram_id(message.from_user.id)
    if user is None and message.from_user.id == settings.super_admin_telegram_id:
        role = "SUPER_ADMIN"
    elif user is not None:
        role = user.role.value
    else:
        await message.answer(
            "Sizning Telegram hisobingiz hali Hisobchiga ulanmagan. "
            "Administrator hisobingizni ulashi kerak."
        )
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Mini Appni ochish",
                    web_app=WebAppInfo(url="http://localhost:5173"),
                )
            ]
        ]
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
