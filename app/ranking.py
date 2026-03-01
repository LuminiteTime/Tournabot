"""Расчёт мест внутри таблиц и в общем зачёте.

Правила:
- 2 очка за победу, 1 за поражение
- При равных очках — отношение суммы выигранных мячей к проигранным
- При полном равенстве — требуется решение пользователя (возвращается флаг)
"""

from __future__ import annotations


def calculate_table_rankings(
    table_size: int,
    matches: dict[str, dict],
    players: list[str],
) -> list[dict]:
    """
    Рассчитать места в одной таблице.

    Возвращает список словарей (отсортирован по убыванию результатов):
        [{"pos": 1-based, "name": str, "points": int,
          "wins_sum": int, "losses_sum": int, "place": int}, ...]

    Если есть неразрешимые ничьи, у нескольких игроков place будет одинаковым —
    вызывающий код должен предложить пользователю разрешить ничью.
    """
    # Собираем статистику по каждому игроку
    stats: list[dict] = []
    for i in range(1, table_size + 1):
        points = 0
        wins_sum = 0
        losses_sum = 0
        matches_played = 0
        for j in range(1, table_size + 1):
            if i == j:
                continue
            key = f"{min(i, j)}_{max(i, j)}"
            match = matches.get(key)
            if not match or match["status"] != "finished":
                continue
            matches_played += 1
            # score1 — очки игрока min(i,j), score2 — max(i,j)
            if i == min(i, j):
                my_score, opp_score = match["score1"], match["score2"]
            else:
                my_score, opp_score = match["score2"], match["score1"]
            if my_score > opp_score:
                points += 2
            else:
                points += 1
            wins_sum += my_score
            losses_sum += opp_score

        # float('inf') не сериализуется в JSON — используем большое число
        ratio = wins_sum / losses_sum if losses_sum > 0 else 99999.0
        stats.append(
            {
                "pos": i,
                "name": players[i - 1],
                "points": points,
                "wins_sum": wins_sum,
                "losses_sum": losses_sum,
                "ratio": ratio,
            }
        )

    # Сортировка: больше очков → лучшее отношение → лучше
    stats.sort(key=lambda s: (s["points"], s["ratio"]), reverse=True)

    # Расставляем места (одинаковые при полном совпадении)
    for idx, s in enumerate(stats):
        if idx == 0:
            s["place"] = 1
        else:
            prev = stats[idx - 1]
            if s["points"] == prev["points"] and s["ratio"] == prev["ratio"]:
                s["place"] = prev["place"]  # ничья — тот же номер места
            else:
                s["place"] = idx + 1

    return stats


def find_unresolved_ties(rankings: list[dict]) -> list[list[dict]]:
    """
    Найти группы игроков с одинаковым местом (неразрешённые ничьи).

    Возвращает список групп, каждая содержит ≥2 игрока с одинаковым place.
    """
    from collections import defaultdict

    groups: dict[int, list[dict]] = defaultdict(list)
    for r in rankings:
        groups[r["place"]].append(r)
    return [g for g in groups.values() if len(g) > 1]


def calculate_overall_rankings(
    all_table_rankings: list[list[dict]],
) -> list[dict]:
    """
    Общий зачёт — чередование мест из таблиц.

    1-е место таблицы 1 → 1-е общее
    1-е место таблицы 2 → 2-е общее
    2-е место таблицы 1 → 3-е общее
    ...
    """
    num_tables = len(all_table_rankings)
    max_places = max(len(t) for t in all_table_rankings)

    overall: list[dict] = []
    place = 1
    for rank_idx in range(max_places):
        for t_idx in range(num_tables):
            if rank_idx < len(all_table_rankings[t_idx]):
                entry = all_table_rankings[t_idx][rank_idx]
                overall.append(
                    {
                        "overall_place": place,
                        "name": entry["name"],
                        "table": t_idx + 1,
                        "table_place": entry["place"],
                        "points": entry["points"],
                        "wins_sum": entry["wins_sum"],
                        "losses_sum": entry["losses_sum"],
                    }
                )
                place += 1

    return overall
