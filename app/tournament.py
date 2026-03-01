"""Сервисный слой — управление жизненным циклом турнира.

Хранит состояние в JSONB-поле модели Tournament.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.combinations import get_combinations
from app.distribution import distribute_snake
from app.models import Tournament
from app.rounds import get_match_round


class TournamentService:
    """CRUD и бизнес-логика турниров."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── CRUD ────────────────────────────────────────────────────────────

    async def get_or_create(self, chat_id: int) -> Tournament:
        """Получить существующий или создать новый турнир для чата."""
        t = await self.get(chat_id)
        if t is None:
            t = Tournament(chat_id=chat_id, data={"status": "menu"})
            self.session.add(t)
            await self.session.commit()
            await self.session.refresh(t)
        return t

    async def get(self, chat_id: int) -> Optional[Tournament]:
        result = await self.session.execute(
            select(Tournament).where(Tournament.chat_id == chat_id)
        )
        return result.scalar_one_or_none()

    async def save(self, tournament: Tournament) -> None:
        """Принудительно обновить JSONB и сохранить."""
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(tournament, "data")
        self.session.add(tournament)
        await self.session.commit()

    async def delete(self, tournament: Tournament) -> None:
        await self.session.delete(tournament)
        await self.session.commit()

    # ── Операции над состоянием ────────────────────────────────────────

    @staticmethod
    def create_tables(players: list[str], table_sizes: list[int]) -> list[dict]:
        """Создать таблицы, распределить игроков, заполнить матчи с раундами."""
        sorted_sizes = sorted(table_sizes, reverse=True)
        distributed = distribute_snake(players, sorted_sizes)
        tables: list[dict] = []
        for size, table_players in zip(sorted_sizes, distributed):
            matches: dict[str, dict] = {}
            for i in range(1, size + 1):
                for j in range(i + 1, size + 1):
                    rnd = get_match_round(size, i, j)
                    matches[f"{i}_{j}"] = {
                        "score1": None,
                        "score2": None,
                        "status": "pending",
                        "round": rnd,
                    }
            tables.append(
                {"size": size, "players": table_players, "matches": matches}
            )
        return tables

    @staticmethod
    def current_round(table: dict) -> int:
        """Номер самого раннего незавершённого раунда (-1, если все сыграны)."""
        min_round: Optional[int] = None
        for m in table["matches"].values():
            if m["status"] != "finished":
                r = m["round"]
                if min_round is None or r < min_round:
                    min_round = r
        return min_round if min_round is not None else -1

    @staticmethod
    def playing_players(table: dict) -> set[int]:
        """Множество позиций игроков, которые сейчас в активном матче."""
        playing: set[int] = set()
        for key, m in table["matches"].items():
            if m["status"] == "playing":
                p1, p2 = map(int, key.split("_"))
                playing.add(p1)
                playing.add(p2)
        return playing

    @staticmethod
    def available_matches(table: dict) -> set[str]:
        """Ключи матчей, доступных для начала (подсвечиваются зелёным)."""
        cur = TournamentService.current_round(table)
        if cur == -1:
            return set()
        busy = TournamentService.playing_players(table)
        avail: set[str] = set()
        for key, m in table["matches"].items():
            if m["status"] == "pending" and m["round"] == cur:
                p1, p2 = map(int, key.split("_"))
                if p1 not in busy and p2 not in busy:
                    avail.add(key)
        return avail

    @staticmethod
    def all_finished(tables: list[dict]) -> bool:
        """Все ли матчи во всех таблицах завершены."""
        return all(
            m["status"] == "finished"
            for t in tables
            for m in t["matches"].values()
        )
