from typing import Dict, Any, Callable, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from bot.data.accessor import UserAccessor


class UsernameUpdateMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if event.from_user.username is None:
            return
        if UserAccessor.user_registered(event.from_user.id):
            user = UserAccessor.convert_tg_user(event.from_user)
            if user.tg_username != event.from_user.username:
                user.tg_username = event.from_user.username
                user.save()
        return await handler(event, data)
