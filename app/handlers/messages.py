"""Обработчики текстовых сообщений — ввод названия, игроков, счёта, подтверждения."""

from __future__ import annotations

from aiogram import Router
from aiogram.types import Message

from app.combinations import get_combinations
from app.db import async_session
from app.handlers.helpers import finish_tournament, show_table, _esc
from app.keyboards import cancel_kb, combinations_kb, table_grid_kb
from app.tournament import TournamentService

router = Router()


@router.message()
async def handle_text(message: Message) -> None:
    """
    Единый обработчик текста. Действие определяется текущим статусом турнира.
    """
    if not message.text:
        return

    async with async_session() as session:
        svc = TournamentService(session)
        t = await svc.get(message.chat.id)
        if not t:
            return

        data = t.data
        status = data.get("status")

        if status == "naming":
            await _handle_naming(message, t, svc)
        elif status == "entering_players":
            await _handle_players(message, t, svc)
        elif status == "playing" and data.get("awaiting_score"):
            await _handle_score(message, t, svc)
        elif status == "playing" and data.get("awaiting_finish_confirm"):
            await _handle_finish_confirm(message, t, svc)


# ── Ввод названия турнира ──────────────────────────────────────────────

async def _handle_naming(msg: Message, t, svc: TournamentService) -> None:
    name = msg.text.strip()
    if not name:
        return

    data = t.data
    data["name"] = name
    data["status"] = "entering_players"
    t.data = data
    await svc.save(t)

    _delete_user_msg(msg)

    await msg.bot.edit_message_text(
        f"🏓 <b>Турнир: {_esc(name)}</b>\n\n"
        "📝 Введите список игроков через запятую:",
        chat_id=msg.chat.id,
        message_id=t.message_id,
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )


# ── Ввод списка игроков ────────────────────────────────────────────────

async def _handle_players(msg: Message, t, svc: TournamentService) -> None:
    players = [p.strip() for p in msg.text.split(",") if p.strip()]
    data = t.data
    name = data["name"]

    _delete_user_msg(msg)

    # Валидация количества
    if len(players) < 4:
        await msg.bot.edit_message_text(
            f"🏓 <b>Турнир: {_esc(name)}</b>\n\n"
            "⚠️ Минимум 4 игрока!\n"
            "📝 Введите список игроков через запятую:",
            chat_id=msg.chat.id,
            message_id=t.message_id,
            reply_markup=cancel_kb(),
            parse_mode="HTML",
        )
        return

    if len(players) > 12:
        await msg.bot.edit_message_text(
            f"🏓 <b>Турнир: {_esc(name)}</b>\n\n"
            "⚠️ Максимум 12 игроков!\n"
            "📝 Введите список игроков через запятую:",
            chat_id=msg.chat.id,
            message_id=t.message_id,
            reply_markup=cancel_kb(),
            parse_mode="HTML",
        )
        return

    data["players"] = players
    options = get_combinations(len(players))

    if len(options) == 1:
        # Единственный вариант — сразу создаём таблицы
        _, table_sizes = options[0]
        tables = TournamentService.create_tables(players, table_sizes)
        data["tables"] = tables
        data["current_table"] = 0
        data["status"] = "playing"
        data["awaiting_score"] = None
        data["awaiting_finish_confirm"] = False
        t.data = data
        await svc.save(t)

        await show_table(msg.bot, msg.chat.id, t.message_id, data, 0)
    else:
        # Есть выбор — показать варианты
        data["status"] = "choosing_combination"
        t.data = data
        await svc.save(t)

        players_preview = ", ".join(players)
        await msg.bot.edit_message_text(
            f"🏓 <b>Турнир: {_esc(name)}</b>\n"
            f"👥 Игроки ({len(players)}): {_esc(players_preview)}\n\n"
            "Выберите формат таблиц:",
            chat_id=msg.chat.id,
            message_id=t.message_id,
            reply_markup=combinations_kb(options),
            parse_mode="HTML",
        )


# ── Ввод счёта матча ───────────────────────────────────────────────────

async def _handle_score(msg: Message, t, svc: TournamentService) -> None:
    data = t.data
    score_info = data["awaiting_score"]
    text = msg.text.strip()

    # Удаляем сообщение пользователя
    _delete_user_msg(msg)

    # Удаляем промпт бота
    try:
        await msg.bot.delete_message(msg.chat.id, score_info["prompt_msg_id"])
    except Exception:
        pass

    # Валидация формата
    error = _validate_score(text)
    if error:
        table = data["tables"][score_info["table_idx"]]
        p1 = table["players"][score_info["row"] - 1]
        p2 = table["players"][score_info["col"] - 1]
        prompt = await msg.bot.send_message(
            msg.chat.id,
            f"⚠️ {error}\n\n"
            f"Введите счёт для матча\n"
            f"<b>{_esc(p1)}</b> : <b>{_esc(p2)}</b>\n\n"
            f"Формат: <code>счёт:счёт</code>",
            parse_mode="HTML",
        )
        data["awaiting_score"]["prompt_msg_id"] = prompt.message_id
        t.data = data
        await svc.save(t)
        return

    # Парсим счёт
    parts = text.split(":")
    s1, s2 = int(parts[0].strip()), int(parts[1].strip())

    # Записываем результат
    ti = score_info["table_idx"]
    row, col = score_info["row"], score_info["col"]
    key = f"{row}_{col}"
    data["tables"][ti]["matches"][key]["score1"] = s1
    data["tables"][ti]["matches"][key]["score2"] = s2
    data["tables"][ti]["matches"][key]["status"] = "finished"
    data["awaiting_score"] = None
    t.data = data
    await svc.save(t)

    # Обновляем основное сообщение
    current = data.get("current_table", 0)
    await show_table(msg.bot, msg.chat.id, t.message_id, data, current)


# ── Подтверждение завершения ───────────────────────────────────────────

async def _handle_finish_confirm(msg: Message, t, svc: TournamentService) -> None:
    text = msg.text.strip().lower()
    _delete_user_msg(msg)

    data = t.data

    if text in ("да", "yes", "д", "y"):
        data["awaiting_finish_confirm"] = False
        t.data = data
        await svc.save(t)
        await finish_tournament(msg.bot, msg.chat.id, t, svc)

    elif text in ("нет", "no", "н", "n"):
        data["awaiting_finish_confirm"] = False
        t.data = data
        await svc.save(t)
        current = data.get("current_table", 0)
        await show_table(msg.bot, msg.chat.id, t.message_id, data, current)


# ── Вспомогательные ────────────────────────────────────────────────────

def _validate_score(text: str) -> str | None:
    """Проверить формат счёта. Вернуть текст ошибки или None."""
    parts = text.split(":")
    if len(parts) != 2:
        return "Неверный формат. Используйте: счёт:счёт"
    try:
        s1, s2 = int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        return "Введите числа в формате счёт:счёт"
    if s1 < 0 or s2 < 0:
        return "Счёт не может быть отрицательным"
    if s1 == s2:
        return "Счёт не может быть равным"
    return None


def _delete_user_msg(msg: Message) -> None:
    """Удалить сообщение пользователя (fire-and-forget)."""
    import asyncio

    loop = asyncio.get_running_loop()
    loop.create_task(_try_delete(msg))


async def _try_delete(msg: Message) -> None:
    try:
        await msg.delete()
    except Exception:
        pass
