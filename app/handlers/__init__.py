"""Регистрация роутеров обработчиков."""

from aiogram import Router

from app.handlers.callbacks import router as cb_router
from app.handlers.messages import router as msg_router
from app.handlers.start import router as start_router

# Порядок важен: start → callbacks → messages (fallback)
routers: list[Router] = [start_router, cb_router, msg_router]
