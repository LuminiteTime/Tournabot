"""SQLAlchemy-модели для хранения турниров."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Tournament(Base):
    """Активный или завершённый турнир в конкретном чате."""

    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Один активный турнир на чат
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    # id сообщения бота (единственное рабочее сообщение)
    message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    # Всё состояние турнира хранится в JSON
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BugReport(Base):
    """Баг-репорт от пользователя (просмотр/закрытие доступно админу)."""

    __tablename__ = "bug_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reporter_chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    reporter_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    # Alias отправителя в формате @username
    reporter_alias: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    done_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
