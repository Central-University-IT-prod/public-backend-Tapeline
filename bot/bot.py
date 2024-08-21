"""
Main bot file
"""

from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

import bot.settings as settings
from bot.data import models
from bot.data.accessor import UserAccessor, TripAccessor
from bot.dialog import (register_dialog, main_menu_dialog, trip_list_dialog,
                        trip_detail_dialog, point_list_dialog, point_detail_dialog,
                        note_list_dialog, note_detail_dialog, participant_list_dialog,
                        commons, settings_dialog, explore_travellers_dialog,
                        debt_list_dialog)
from bot.middleware.username import UsernameUpdateMiddleware


class AppBot(Bot):
    """
    Main bot class
    """
    dispatcher = Dispatcher()
    router = Router()

    def __init__(self):
        super().__init__(settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
        models.init()

    async def run(self):
        """
        Starts the bot
        """
        self.dispatcher.include_router(self.router)
        self.dispatcher.include_router(register_dialog.router)
        self.dispatcher.include_router(main_menu_dialog.router)
        self.dispatcher.include_router(trip_list_dialog.router)
        self.dispatcher.include_router(trip_detail_dialog.router)
        self.dispatcher.include_router(point_list_dialog.router)
        self.dispatcher.include_router(point_detail_dialog.router)
        self.dispatcher.include_router(note_list_dialog.router)
        self.dispatcher.include_router(note_detail_dialog.router)
        self.dispatcher.include_router(participant_list_dialog.router)
        self.dispatcher.include_router(settings_dialog.router)
        self.dispatcher.include_router(explore_travellers_dialog.router)
        self.dispatcher.include_router(debt_list_dialog.router)
        self.router.message.middleware(UsernameUpdateMiddleware())
        await self.dispatcher.start_polling(self)


@AppBot.dispatcher.message(Command("start"))
async def start(message: Message, state) -> None:
    """
    Handle /start command
    """
    if not UserAccessor.user_registered(message.from_user.id):
        await register_dialog.init_dialog(message, state)
    else:
        if message.from_user.username is not None:
            if UserAccessor.user_registered(message.from_user.id):
                user = UserAccessor.convert_tg_user(message.from_user)
                if user.tg_username != message.from_user.username:
                    user.tg_username = message.from_user.username
                    user.save()
        await main_menu_dialog.init_dialog(message, state)


@AppBot.dispatcher.message(F.text.startswith("/join-"))
async def _join(message: Message, state) -> None:
    """
    Handle /join-<key> commands
    """
    if not UserAccessor.user_registered(message.from_user.id):
        await message.answer("⚠️ <b>Notice!</b>\n\n"
                             "You've tried to join some trip, but you do not "
                             "have a Travelagent account yet.\n"
                             "Perform registration first, and then re-enter"
                             "join command")
        await register_dialog.init_dialog(message, state)
    else:
        try:
            trip = TripAccessor.get_trip_to_join(message.text[6:], message.from_user.id)
        except ValueError as e:
            await commons.send_error(message, e.args[0])
            return
        for user in trip.participants:
            await message.bot.send_message(user.tg_id,
                                           f"👥 {message.from_user.full_name} joined trip {trip.name}")
        await message.bot.send_message(trip.owner.tg_id,
                                       f"👥 {message.from_user.full_name} joined trip {trip.name}")
        trip.participants.add(UserAccessor.convert_tg_user(message.from_user))
        trip.save()
        await message.answer("✅ <b>Successfully joined the trip!</b>")
        await main_menu_dialog.init_dialog(message, state)
