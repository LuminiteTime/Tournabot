"""Общие утилиты для обработчиков — завершение турнира, редактирование сообщения."""

from __future__ import annotations

from aiogram import Bot
from aiogram.types import BufferedInputFile

from app.excel_export import create_results_excel
from app.json_export import create_results_json
from app.keyboards import table_grid_kb, tie_resolve_kb
from app.models import Tournament
from app.ranking import (
    calculate_overall_rankings,
    calculate_table_rankings,
    find_unresolved_ties,
)
from app.tournament import TournamentService


def table_message_text(data: dict, table_idx: int) -> str:
    """Сформировать текст сообщения для экрана таблицы."""
    table = data["tables"][table_idx]
    lines = [
        f"🏓 <b>{_esc(data['name'])}</b>",
        f"📊 Таблица {table_idx + 1} — {table['size']} игроков",
        "",
    ]
    for i, name in enumerate(table["players"], 1):
        lines.append(f"  {i}. {_esc(name)}")
    return "\n".join(lines)


def _esc(text: str) -> str:
    """Экранировать HTML-спецсимволы."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def show_table(bot: Bot, chat_id: int, message_id: int, data: dict, table_idx: int) -> None:
    """Отредактировать основное сообщение — показать таблицу."""
    text = table_message_text(data, table_idx)
    await bot.edit_message_text(
        text,
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=table_grid_kb(data, table_idx),
        parse_mode="HTML",
    )


def _apply_tie_overrides_to_rankings(
    rankings: list[dict], overrides: dict[str, int]
) -> list[dict]:
    """Применить пользовательские решения к рейтингу таблицы."""
    if not overrides:
        return rankings

    def sort_key(entry: dict) -> tuple:
        bonus = 0
        for key, winner_pos in overrides.items():
            positions = list(map(int, key.split("_")))
            if entry["pos"] in positions:
                bonus = 1 if entry["pos"] == winner_pos else -1
        return (-entry["place"], bonus, -entry["points"], -entry.get("ratio", 0))

    rankings.sort(key=sort_key, reverse=True)
    for idx, r in enumerate(rankings):
        r["place"] = idx + 1
    return rankings


async def finish_tournament(
    bot: Bot,
    chat_id: int,
    tournament: Tournament,
    svc: TournamentService,
) -> None:
    """
    Завершить турнир: рассчитать места, отправить Excel, показать итоги.

    Если есть неразрешимые ничьи — вместо финальных результатов показать
    кнопку разрешения ничьи.
    """
    data = tournament.data
    tie_overrides = data.get("tie_overrides", {})
    all_rankings: list[list[dict]] = []

    for ti, table in enumerate(data["tables"]):
        rankings = calculate_table_rankings(
            table["size"], table["matches"], table["players"]
        )
        # Применяем ранее сохранённые решения по ничьям
        overrides = tie_overrides.get(str(ti), {})
        rankings = _apply_tie_overrides_to_rankings(rankings, overrides)
        all_rankings.append(rankings)

    # Проверяем оставшиеся неразрешённые ничьи
    for t_idx, rankings in enumerate(all_rankings):
        overrides = tie_overrides.get(str(t_idx), {})
        ties = find_unresolved_ties(rankings)
        for group in ties:
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    tk = f"{min(a['pos'], b['pos'])}_{max(a['pos'], b['pos'])}"
                    if tk not in overrides:
                        data["status"] = "resolving_ties"
                        tournament.data = data
                        await svc.save(tournament)

                        await bot.edit_message_text(
                            f"⚖️ <b>Ничья в таблице {t_idx + 1}!</b>\n\n"
                            f"{_esc(a['name'])} и {_esc(b['name'])} имеют одинаковые очки "
                            f"({a['points']}) и отношение ({a['wins_sum']}:{a['losses_sum']}).\n\n"
                            "Кто занимает место выше?",
                            chat_id=chat_id,
                            message_id=tournament.message_id,
                            reply_markup=tie_resolve_kb(t_idx, a, b),
                            parse_mode="HTML",
                        )
                        return

    # Нет ничьих — финализируем
    overall = calculate_overall_rankings(all_rankings)

    # Excel-файл
    excel_bytes = create_results_excel(data, all_rankings, overall)
    await bot.send_document(
        chat_id,
        BufferedInputFile(
            excel_bytes, filename=f"{data['name']}_results.xlsx"
        ),
        caption="📊 Результаты турнира",
    )

    # JSON-файл для импорта
    json_bytes = create_results_json(data)
    await bot.send_document(
        chat_id,
        BufferedInputFile(
            json_bytes, filename=f"{data['name']}_results.json"
        ),
        caption="📁 JSON для импорта",
    )

    # Текстовые результаты
    lines = [f"🏆 <b>Результаты «{_esc(data['name'])}»</b>\n"]
    for t_idx, (table, rankings) in enumerate(zip(data["tables"], all_rankings)):
        lines.append(f"📊 <b>Таблица {t_idx + 1}:</b>")
        for r in rankings:
            lines.append(
                f"  {r['place']}. {_esc(r['name'])} — {r['points']} очк. "
                f"({r['wins_sum']}:{r['losses_sum']})"
            )
        lines.append("")

    lines.append("🥇 <b>Общий зачёт:</b>")
    for o in overall:
        lines.append(
            f"  {o['overall_place']}. {_esc(o['name'])} (табл. {o['table']})"
        )

    await bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML")

    # Обновляем главное сообщение
    data["status"] = "finished"
    tournament.data = data
    await svc.save(tournament)

    await bot.edit_message_text(
        f"✅ <b>Турнир «{_esc(data['name'])}» завершён!</b>\n\n"
        "Для нового турнира — /start",
        chat_id=chat_id,
        message_id=tournament.message_id,
        parse_mode="HTML",
    )
