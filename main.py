import asyncio
import logging
import sys

import bot.bot


async def main():
    app = bot.bot.AppBot()
    await app.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

# import asyncio
# import os
# from typing import Dict, Any
#
# from aiogram.filters import CommandStart
# from aiogram.fsm.state import State, StatesGroup
#
# from aiogram import Router, F, Bot, Dispatcher
# from aiogram.types import Message
#
# from aiogram_dialog import Dialog, Window, setup_dialogs, DialogManager
# from aiogram_dialog.widgets.text import Format, Const
# from aiogram_dialog.widgets.kbd import Checkbox, Button, Row, Cancel, Start
#
#
# class MainMenu(StatesGroup):
#     START = State()
#
#
# class Settings(StatesGroup):
#     START = State()
#
#
# main_menu = Dialog(
#     Window(
#         Format(
#             "Hello, {event.from_user.username}. \n\n"
#             "Extended mode is.\n"
#         ),
#         Row(
#             Start(Const("Settings"), id="settings", state=Settings.START),
#         ),
#         state=MainMenu.START
#     )
# )
#
# settings = Dialog(
#     Window(
#         Const("Settings"),
#         Row(
#             Cancel(),
#             Cancel(text=Const("Save"), id="save"),
#         ),
#         state=Settings.START,
#     )
# )
#
# router = Router()
#
#
# @router.message(CommandStart())
# async def start(message: Message, dialog_manager: DialogManager):
#     await dialog_manager.start(MainMenu.START)
#
#
# async def main():
#     bot = Bot(token="secret")
#     dp = Dispatcher()
#     dp.include_router(main_menu)
#     dp.include_router(settings)
#     dp.include_router(router)
#     setup_dialogs(dp)
#
#     await dp.start_polling(bot)
#
#
# asyncio.run(main())