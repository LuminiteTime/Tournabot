"""Обработчик команды /start — точка входа."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db import async_session
from app.keyboards import menu_kb
from app.tournament import TournamentService

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Показать главное меню (одно сообщение, которое потом редактируется)."""
    async with async_session() as session:
        svc = TournamentService(session)
        t = await svc.get_or_create(message.chat.id)

        # Сброс состояния
        t.data = {"status": "menu"}

        sent = await message.answer(
            "🏓 <b>TournaBot — Турниры по настольному теннису</b>\n\n"
            "Нажмите кнопку, чтобы начать новый турнир.",
            reply_markup=menu_kb(),
            parse_mode="HTML",
        )
        t.message_id = sent.message_id
        await svc.save(t)

    # Удаляем команду пользователя
    try:
        await message.delete()
    except Exception:
        pass
