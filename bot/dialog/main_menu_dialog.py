from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot.dialog import trip_list_dialog


class MainMenuDialogStates(StatesGroup):
    START = State()


router = Router()
menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✈️ Trips", callback_data="trips")],
    [InlineKeyboardButton(text="🤝 Explore travellers", callback_data="explore")],
    [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
])


async def init_dialog(message: Message, state: FSMContext):
    await state.set_state(MainMenuDialogStates.START)
    await message.answer("👋 <b>Welcome back to the Travelagent bot.</b>",
                         reply_markup=menu_keyboard)


@router.callback_query(F.data == "trips")
async def trips(callback_query: CallbackQuery, state: FSMContext):
    await trip_list_dialog.init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "settings")
async def trips(callback_query: CallbackQuery, state: FSMContext):
    from bot.dialog import settings_dialog
    await settings_dialog.init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "explore")
async def trips(callback_query: CallbackQuery, state: FSMContext):
    from bot.dialog import explore_travellers_dialog
    await explore_travellers_dialog.init_dialog(callback_query.message, state, callback_query.from_user)

