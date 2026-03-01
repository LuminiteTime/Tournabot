"""Распределение игроков по таблицам «змейкой».

Пример для таблиц [6, 5, 4] и игроков P1..P15:
  Проход →: P1→T1, P2→T2, P3→T3
  Проход ←: P4→T3, P5→T2, P6→T1
  Проход →: P7→T1, P8→T2, P9→T3
  ...
"""

from __future__ import annotations


def distribute_snake(players: list[str], table_sizes: list[int]) -> list[list[str]]:
    """
    Распределить игроков змейкой по таблицам.

    Параметры:
        players: список имён в порядке рейтинга / ввода
        table_sizes: размеры таблиц (будут отсортированы по убыванию)

    Возвращает:
        Список таблиц, каждая — список имён игроков по позициям.
    """
    sorted_sizes = sorted(table_sizes, reverse=True)
    num_tables = len(sorted_sizes)
    tables: list[list[str]] = [[] for _ in range(num_tables)]

    player_idx = 0
    total = len(players)
    forward = True

    while player_idx < total:
        indices = range(num_tables) if forward else range(num_tables - 1, -1, -1)
        for t in indices:
            if player_idx >= total:
                break
            # Добавляем только если в таблице ещё есть место
            if len(tables[t]) < sorted_sizes[t]:
                tables[t].append(players[player_idx])
                player_idx += 1
        forward = not forward

    return tables
