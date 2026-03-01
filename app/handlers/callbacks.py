"""Обработчики callback-запросов (нажатия на инлайн-кнопки)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.db import async_session
from app.handlers.helpers import (
    _apply_tie_overrides_to_rankings,
    _esc,
    finish_tournament,
    show_table,
)
from app.keyboards import cancel_kb, combinations_kb, menu_kb, table_grid_kb, tie_resolve_kb
from app.combinations import get_combinations
from app.ranking import calculate_table_rankings, find_unresolved_ties
from app.tournament import TournamentService

router = Router()


# ── Заглушка для неактивных кнопок ──────────────────────────────────────

@router.callback_query(F.data == "nop")
async def nop(cb: CallbackQuery) -> None:
    await cb.answer()


# ── Главное меню → Начать турнир ────────────────────────────────────────

@router.callback_query(F.data == "start")
async def start_tournament(cb: CallbackQuery) -> None:
    async with async_session() as session:
        svc = TournamentService(session)
        t = await svc.get(cb.message.chat.id)
        if not t:
            await cb.answer("Используйте /start")
            return
        t.data = {"status": "naming"}
        await svc.save(t)

    await cb.message.edit_text(
        "✏️ <b>Введите название турнира:</b>",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await cb.answer()


# ── Отмена → Главное меню ──────────────────────────────────────────────

@router.callback_query(F.data == "cancel")
async def cancel(cb: CallbackQuery) -> None:
    async with async_session() as session:
        svc = TournamentService(session)
        t = await svc.get(cb.message.chat.id)
        if not t:
            return
        t.data = {"status": "menu"}
        await svc.save(t)

    await cb.message.edit_text(
        "🏓 <b>TournaBot — Турниры по настольному теннису</b>\n\n"
        "Нажмите кнопку, чтобы начать новый турнир.",
        reply_markup=menu_kb(),
        parse_mode="HTML",
    )
    await cb.answer()


# ── Выбор комбинации таблиц ────────────────────────────────────────────

@router.callback_query(F.data.startswith("comb:"))
async def choose_combination(cb: CallbackQuery) -> None:
    comb_idx = int(cb.data.split(":")[1])

    async with async_session() as session:
        svc = TournamentService(session)
        t = await svc.get(cb.message.chat.id)
        if not t or t.data.get("status") != "choosing_combination":
            await cb.answer("Ошибка состояния")
            return

        data = t.data
        players = data["players"]
        options = get_combinations(len(players))
        _, table_sizes = options[comb_idx]

        tables = TournamentService.create_tables(players, table_sizes)
        data["tables"] = tables
        data["current_table"] = 0
        data["status"] = "playing"
        data["awaiting_score"] = None
        data["awaiting_finish_confirm"] = False

        t.data = data
        await svc.save(t)

    await show_table(cb.bot, cb.message.chat.id, t.message_id, data, 0)
    await cb.answer()


# ── Переключение между таблицами ───────────────────────────────────────

@router.callback_query(F.data.startswith("tbl:"))
async def switch_table(cb: CallbackQuery) -> None:
    table_idx = int(cb.data.split(":")[1])

    async with async_session() as session:
        svc = TournamentService(session)
        t = await svc.get(cb.message.chat.id)
        if not t or t.data.get("status") != "playing":
            await cb.answer("Ошибка")
            return

        data = t.data
        data["current_table"] = table_idx
        t.data = data
        await svc.save(t)

    await show_table(cb.bot, cb.message.chat.id, t.message_id, data, table_idx)
    await cb.answer()


# ── Клик по кнопке матча ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("m:"))
async def match_click(cb: CallbackQuery) -> None:
    parts = cb.data.split(":")
    table_idx, row, col = int(parts[1]), int(parts[2]), int(parts[3])

    async with async_session() as session:
        svc = TournamentService(session)
        t = await svc.get(cb.message.chat.id)
        if not t or t.data.get("status") != "playing":
            await cb.answer("Ошибка")
            return

        data = t.data
        table = data["tables"][table_idx]
        key = f"{row}_{col}"
        match = table["matches"][key]

        if match["status"] == "pending":
            # ── Начать матч (отметить как играющийся) ──
            # Если ожидается ввод счёта другого матча — отменяем
            if data.get("awaiting_score"):
                try:
                    await cb.bot.delete_message(
                        cb.message.chat.id,
                        data["awaiting_score"]["prompt_msg_id"],
                    )
                except Exception:
                    pass
                data["awaiting_score"] = None

            match["status"] = "playing"
            t.data = data
            await svc.save(t)

            current = data.get("current_table", 0)
            await show_table(cb.bot, cb.message.chat.id, t.message_id, data, current)
            await cb.answer("Матч начат!")

        elif match["status"] == "playing":
            # ── Запросить ввод счёта ──
            # Если уже ждём ввод для другого матча — удаляем старый промпт
            if data.get("awaiting_score"):
                try:
                    await cb.bot.delete_message(
                        cb.message.chat.id,
                        data["awaiting_score"]["prompt_msg_id"],
                    )
                except Exception:
                    pass

            p1_name = table["players"][row - 1]
            p2_name = table["players"][col - 1]
            prompt = await cb.message.answer(
                f"Введите счёт для матча\n"
                f"<b>{p1_name}</b> : <b>{p2_name}</b>\n\n"
                f"Формат: <code>счёт:счёт</code>",
                parse_mode="HTML",
            )
            data["awaiting_score"] = {
                "table_idx": table_idx,
                "row": row,
                "col": col,
                "prompt_msg_id": prompt.message_id,
            }
            t.data = data
            await svc.save(t)
            await cb.answer()

        elif match["status"] == "finished":
            await cb.answer("Матч уже сыгран")


# ── Завершить турнир ───────────────────────────────────────────────────

@router.callback_query(F.data == "finish")
async def finish(cb: CallbackQuery) -> None:
    async with async_session() as session:
        svc = TournamentService(session)
        t = await svc.get(cb.message.chat.id)
        if not t or t.data.get("status") != "playing":
            await cb.answer("Ошибка")
            return

        data = t.data

        if TournamentService.all_finished(data["tables"]):
            # Все матчи сыграны — финишируем
            await finish_tournament(cb.bot, cb.message.chat.id, t, svc)
            await cb.answer()
        else:
            # Не все — просим подтверждение через текстовое сообщение
            data["awaiting_finish_confirm"] = True
            t.data = data
            await svc.save(t)

            await cb.message.edit_text(
                "⚠️ <b>Не все матчи сыграны!</b>\n\n"
                "Вы уверены, что хотите завершить турнир?\n"
                "Напишите <b>Да</b> или <b>Нет</b>",
                parse_mode="HTML",
            )
            await cb.answer()


# ── Разрешение ничьей ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("tie:"))
async def resolve_tie(cb: CallbackQuery) -> None:
    """
    Формат: tie:<table_idx>:<winner_pos>:<loser_pos>
    Пользователь выбирает, кто из двух равных игроков занимает место выше.
    """
    parts = cb.data.split(":")
    table_idx = int(parts[1])
    winner_pos = int(parts[2])
    loser_pos = int(parts[3])

    async with async_session() as session:
        svc = TournamentService(session)
        t = await svc.get(cb.message.chat.id)
        if not t or t.data.get("status") != "resolving_ties":
            await cb.answer("Ошибка")
            return

        data = t.data

        # Сохраняем решение по ничье
        tie_overrides = data.setdefault("tie_overrides", {})
        k = f"{min(winner_pos, loser_pos)}_{max(winner_pos, loser_pos)}"
        tie_overrides.setdefault(str(table_idx), {})[k] = winner_pos

        # Ищем следующую неразрешённую ничью
        next_tie = _find_next_unresolved_tie(data, tie_overrides)

        if next_tie:
            ti, a, b = next_tie
            t.data = data
            await svc.save(t)
            await cb.message.edit_text(
                f"⚖️ <b>Ничья в таблице {ti + 1}!</b>\n\n"
                f"{_esc(a['name'])} и {_esc(b['name'])} — "
                f"одинаковые очки и отношение.\n\nКто занимает место выше?",
                chat_id=cb.message.chat.id,
                message_id=t.message_id,
                reply_markup=tie_resolve_kb(ti, a, b),
                parse_mode="HTML",
            )
        else:
            # Все ничьи разрешены — финализируем
            data["status"] = "playing"
            t.data = data
            await svc.save(t)
            await finish_tournament(cb.bot, cb.message.chat.id, t, svc)

    await cb.answer()


def _find_next_unresolved_tie(
    data: dict, tie_overrides: dict
) -> tuple[int, dict, dict] | None:
    """Найти первую неразрешённую ничью среди всех таблиц."""
    for ti, table in enumerate(data["tables"]):
        rankings = calculate_table_rankings(
            table["size"], table["matches"], table["players"]
        )
        overrides = tie_overrides.get(str(ti), {})
        rankings = _apply_tie_overrides_to_rankings(rankings, overrides)
        ties = find_unresolved_ties(rankings)
        for group in ties:
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    tk = f"{min(a['pos'], b['pos'])}_{max(a['pos'], b['pos'])}"
                    if tk not in overrides:
                        return (ti, a, b)
    return None
