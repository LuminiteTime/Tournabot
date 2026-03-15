"""Точка входа — запуск бота."""

import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.config import settings
from app.db import init_db
from app.handlers import routers
from app.logging_config import configure_logging

LOG_LEVEL = "INFO"

configure_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Инициализировать БД, зарегистрировать роутеры, запустить polling."""
    logger.info("Инициализация БД...")
    await init_db()

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # Регистрируем все роутеры
    for r in routers:
        dp.include_router(r)

    logger.info("Бот запущен — polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
