"""Конфигурация приложения через переменные окружения."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки бота и БД — читаются из .env или окружения."""

    BOT_TOKEN: str
    # Telegram user id автора/админа (для меню баг-репортов)
    ADMIN_USER_ID: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
