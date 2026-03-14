"""Сервисный слой для баг-репортов."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BugReport


class BugReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        reporter_chat_id: int,
        reporter_user_id: int,
        reporter_alias: str | None,
        text: str,
    ) -> BugReport:
        r = BugReport(
            reporter_chat_id=reporter_chat_id,
            reporter_user_id=reporter_user_id,
            reporter_alias=reporter_alias,
            text=text,
            is_done=False,
        )
        self.session.add(r)
        await self.session.commit()
        await self.session.refresh(r)
        return r

    async def get(self, report_id: int) -> BugReport | None:
        res = await self.session.execute(select(BugReport).where(BugReport.id == report_id))
        return res.scalar_one_or_none()

    async def count_open(self) -> int:
        res = await self.session.execute(
            select(func.count()).select_from(BugReport).where(BugReport.is_done.is_(False))
        )
        return int(res.scalar_one())

    async def list_open(self, limit: int = 20) -> list[BugReport]:
        res = await self.session.execute(
            select(BugReport)
            .where(BugReport.is_done.is_(False))
            .order_by(desc(BugReport.created_at), desc(BugReport.id))
            .limit(limit)
        )
        return list(res.scalars().all())

    async def mark_done(self, report_id: int) -> bool:
        r = await self.get(report_id)
        if not r:
            return False
        if r.is_done:
            return True
        r.is_done = True
        r.done_at = datetime.now(tz=timezone.utc)
        self.session.add(r)
        await self.session.commit()
        return True
