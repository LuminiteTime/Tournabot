"""SQLAlchemy-модели для хранения турниров."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, func
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
