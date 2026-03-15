"""Обработчик команды /start — точка входа."""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bug_reports import BugReportService
from app.config import settings
from app.db import async_session
from app.keyboards import menu_kb
from app.metrics import record_status
from app.tournament import TournamentService

router = Router()
logger = logging.getLogger(__name__)


def _user_alias(message: Message) -> str:
    user = message.from_user
    if not user:
        return "unknown"
    if user.username:
        return f"@{user.username}"
    full_name = " ".join([p for p in [user.first_name, user.last_name] if p])
    return full_name or f"id:{user.id}"


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Показать главное меню (одно сообщение, которое потом редактируется)."""
    async with async_session() as session:
        svc = TournamentService(session)
        t = await svc.get_or_create(message.chat.id)

        # Сброс состояния
        t.data = {"status": "menu"}
        record_status("menu")

        is_admin = message.from_user is not None and message.from_user.id == settings.ADMIN_USER_ID
        open_bug_count = None
        if is_admin:
            open_bug_count = await BugReportService(session).count_open()

        sent = await message.answer(
            "🏓 <b>TournaBot — Турниры по настольному теннису</b>\n\n"
            "Нажмите кнопку, чтобы начать новый турнир.",
            reply_markup=menu_kb(is_admin=is_admin, open_bug_count=open_bug_count),
            parse_mode="HTML",
        )
        t.message_id = sent.message_id
        await svc.save(t)

    logger.info(
        "Главное меню открыто",
        extra={
            "chat_id": message.chat.id,
            "user_id": message.from_user.id if message.from_user else None,
            "alias": _user_alias(message),
        },
    )

    # Удаляем команду пользователя
    try:
        await message.delete()
    except Exception:
        pass
