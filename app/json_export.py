"""Генерация JSON-файла для импорта в другие системы."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta


# Московское время (UTC+3)
_MSK = timezone(timedelta(hours=3))


def create_results_json(data: dict) -> bytes:
    """
    Создать JSON с информацией о турнире и списком матчей.

    Формат:
    {
      "Title": "...",
      "Start Date": "25.12.2025",
      "End Date": "25.12.2025",
      "Matches": [
        {
          "First Player Name": "...",
          "Second Player Name": "...",
          "First Player Score": 11,
          "Second Player Score": 5
        },
        ...
      ]
    }
    """
    today_msk = datetime.now(_MSK).strftime("%d.%m.%Y")

    matches: list[dict] = []
    for table in data["tables"]:
        players = table["players"]
        size = table["size"]
        # Только верхний правый треугольник (i < j)
        for i in range(1, size + 1):
            for j in range(i + 1, size + 1):
                key = f"{i}_{j}"
                m = table["matches"].get(key, {})
                if m.get("status") == "finished":
                    matches.append(
                        {
                            "First Player Name": players[i - 1],
                            "Second Player Name": players[j - 1],
                            "First Player Score": m["score1"],
                            "Second Player Score": m["score2"],
                        }
                    )

    result = {
        "Title": data.get("name", "Tournament"),
        "Start Date": today_msk,
        "End Date": today_msk,
        "Matches": matches,
    }

    return json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")
