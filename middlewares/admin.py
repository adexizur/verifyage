"""
Middleware для проверки администраторов.
"""

from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from config import ADMINS


class AdminWhitelistMiddleware(BaseMiddleware):
    """
    Middleware для проверки принадлежности пользователя к whitelist админов.
    
    Работает только в личных сообщениях с ботом.
    """

    def __init__(self):
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем пользователя из события
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        else:
            return await handler(event, data)

        # Проверяем, является ли пользователь админом
        if user.id not in ADMINS:
            # Если не админ - игнорируем команду
            return None

        # Добавляем флаг админа в данные
        data["is_admin"] = True
        return await handler(event, data)
