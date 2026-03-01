"""Построение инлайн-клавиатур для всех экранов бота.

Стили кнопок (Bot API 9.4):
  "success" — зелёный (доступные для игры матчи)
  "primary" — синий  (текущий играющийся матч)
  "danger"  — красный
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.tournament import TournamentService

# ── Стили кнопок ────────────────────────────────────────────────────────
STYLE_AVAILABLE = "success"  # зелёный — матч можно начать сейчас
STYLE_PLAYING = "primary"    # синий — матч идёт (ближайший к жёлтому)

MAX_NAME_LEN = 9  # максимальная длина имени на кнопке


# ── Утилиты ─────────────────────────────────────────────────────────────

def _btn(text: str, cb: str = "nop", style: str | None = None) -> InlineKeyboardButton:
    """Создать кнопку с опциональным стилем."""
    kw: dict = {"text": text, "callback_data": cb}
    if style:
        kw["style"] = style
    return InlineKeyboardButton(**kw)


def _trunc(name: str) -> str:
    """Обрезать имя до допустимой длины."""
    return name[:MAX_NAME_LEN] + ".." if len(name) > MAX_NAME_LEN else name


# ── Клавиатуры меню ─────────────────────────────────────────────────────

def menu_kb() -> InlineKeyboardMarkup:
    """Главное меню — «Начать турнир»."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[_btn("Начать турнир", "start")]]
    )


def cancel_kb() -> InlineKeyboardMarkup:
    """Кнопка отмены (на этапе ввода текста)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[_btn("Отмена", "cancel")]]
    )


def combinations_kb(options: list[tuple[str, list[int]]]) -> InlineKeyboardMarkup:
    """Выбор формата таблиц: каждая опция — отдельная кнопка."""
    rows = [[_btn(desc, f"comb:{idx}")] for idx, (desc, _) in enumerate(options)]
    rows.append([_btn("Отмена", "cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Клавиатура таблицы матчей ───────────────────────────────────────────

def _match_text(match: dict, is_row_first: bool) -> str:
    """
    Текст на кнопке матча.

    is_row_first=True  → ячейка для игрока строки (верхний правый треугольник)
    is_row_first=False → зеркальная ячейка (нижний левый)
    """
    status = match["status"]
    if status == "pending":
        return "·"
    if status == "playing":
        return "▶"
    # finished — только счёт, без очков
    s1, s2 = match["score1"], match["score2"]
    if is_row_first:
        return f"{s1}:{s2}"
    else:
        return f"{s2}:{s1}"


def _match_style(match: dict, key: str, avail: set[str]) -> str | None:
    """Определить стиль кнопки матча."""
    if match["status"] == "playing":
        return STYLE_PLAYING
    if match["status"] == "pending" and key in avail:
        return STYLE_AVAILABLE
    return None


def table_grid_kb(data: dict, table_idx: int) -> InlineKeyboardMarkup:
    """
    Построить инлайн-клавиатуру — таблицу матчей для указанной таблицы.

    Структура:
      [  ] [1] [2] ... [N]
      [1.Имя] [×] [m] [m] ...
      [2.Имя] [m] [×] [m] ...
      ...
      [◀] [1/N] [▶]          — навигация между таблицами
      [Завершить турнир]
    """
    table = data["tables"][table_idx]
    size = table["size"]
    players = table["players"]
    matches = table["matches"]
    num_tables = len(data["tables"])

    avail = TournamentService.available_matches(table)
    rows: list[list[InlineKeyboardButton]] = []

    # ── Заголовок: пустая ячейка + номера столбцов ──
    header = [_btn("  ")]
    for j in range(1, size + 1):
        header.append(_btn(str(j)))
    rows.append(header)

    # ── Строки игроков ──
    for i in range(1, size + 1):
        row: list[InlineKeyboardButton] = [_btn(f"{i}.{_trunc(players[i - 1])}")]
        for j in range(1, size + 1):
            if i == j:
                # Диагональ
                row.append(_btn("×"))
            elif i < j:
                # Верхний правый треугольник — кликабельная кнопка
                key = f"{i}_{j}"
                m = matches[key]
                text = _match_text(m, is_row_first=True)
                style = _match_style(m, key, avail)
                row.append(_btn(text, f"m:{table_idx}:{i}:{j}", style))
            else:
                # Нижний левый треугольник — зеркало (без стиля и без клика)
                key = f"{j}_{i}"
                m = matches[key]
                text = _match_text(m, is_row_first=False)
                row.append(_btn(text))
        rows.append(row)

    # ── Навигация между таблицами ──
    if num_tables > 1:
        nav: list[InlineKeyboardButton] = []
        if table_idx > 0:
            nav.append(_btn("◀", f"tbl:{table_idx - 1}"))
        nav.append(_btn(f"{table_idx + 1}/{num_tables}"))
        if table_idx < num_tables - 1:
            nav.append(_btn("▶", f"tbl:{table_idx + 1}"))
        rows.append(nav)

    # ── Кнопка завершения ──
    rows.append([_btn("Завершить турнир", "finish")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def tie_resolve_kb(
    table_idx: int, player_a: dict, player_b: dict
) -> InlineKeyboardMarkup:
    """Клавиатура для разрешения ничьи: выбрать, кто выше."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn(
                    f"{player_a['name']} выше",
                    f"tie:{table_idx}:{player_a['pos']}:{player_b['pos']}",
                ),
            ],
            [
                _btn(
                    f"{player_b['name']} выше",
                    f"tie:{table_idx}:{player_b['pos']}:{player_a['pos']}",
                ),
            ],
        ]
    )
