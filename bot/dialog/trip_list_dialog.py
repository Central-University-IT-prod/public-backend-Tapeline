import uuid
from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot.api.nominatim import NominatimAPI
from bot.data.accessor import TripAccessor, UserAccessor
from bot.data.formatter import DateFormatter
from bot.data.models import User, Trip
from bot.dialog import commons


class TripListDialogStates(StatesGroup):
    START = State()
    ADD_PROVIDE_NAME = State()
    ADD_PROVIDE_DESCRIPTION = State()
    ADD_PROVIDE_DATES = State()


router = Router()
menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Add", callback_data="add_trip")],
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
])
cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel_add")]
])
cancel_skip_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➡️ Skip", callback_data="skip")],
    [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel_add")]
])
user_trip_data = {}


def construct_keyboard(user: User):
    trips = TripAccessor.get_all_by_user(user)
    buttons = [[InlineKeyboardButton(text=("👑 " if trip.owner == user else "") + trip.name,
                                     callback_data=f"tr_{trip.get_id()}")]
               for trip in trips]
    return InlineKeyboardMarkup(inline_keyboard=buttons + menu_keyboard.inline_keyboard)


async def init_dialog(message: Message, state: FSMContext, user):
    await state.set_state(TripListDialogStates.START)
    await message.answer("✈️ <b>Your trips.</b>",
                         reply_markup=construct_keyboard(UserAccessor.convert_tg_user(user)))


@router.callback_query(F.data == "back", TripListDialogStates.START)
async def _go_back_btn(callback_query: CallbackQuery, state: FSMContext):
    from bot.dialog import main_menu_dialog
    await main_menu_dialog.init_dialog(callback_query.message, state)


@router.callback_query(F.data == "add_trip", TripListDialogStates.START)
async def _add_btn(callback_query: CallbackQuery, state: FSMContext):
    user_trip_data[callback_query.from_user.id] = {"name": None, "desc": None, "start": None, "end": None}
    await state.set_state(TripListDialogStates.ADD_PROVIDE_NAME)
    await callback_query.message.answer("➕ <b>Add a trip: 1/3.</b>\n\n"
                                        "Please specify the name for your trip.",
                                        reply_markup=cancel_keyboard)


@router.callback_query(F.data == "cancel_add", TripListDialogStates.ADD_PROVIDE_NAME)
@router.callback_query(F.data == "cancel_add", TripListDialogStates.ADD_PROVIDE_DESCRIPTION)
@router.callback_query(F.data == "cancel_add", TripListDialogStates.ADD_PROVIDE_DATES)
async def _cancel_creation(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("✖️ <b>Cancelled.</b>")
    await init_dialog(callback_query.message, state, callback_query.from_user)
    del user_trip_data[callback_query.from_user.id]


@router.message(TripListDialogStates.ADD_PROVIDE_NAME)
async def _name_provided(message: Message, state: FSMContext):
    if Trip.select().where(Trip.name == message.text).exists():
        await commons.send_bad_input(message, "Trip name already occupied")
        return
    user_trip_data[message.from_user.id]["name"] = message.text
    await state.set_state(TripListDialogStates.ADD_PROVIDE_DESCRIPTION)
    await message.answer("➕ <b>Add a trip: 2/3.</b>\n\n"
                         "Please specify the description for your trip.",
                         reply_markup=cancel_skip_keyboard)


@router.message(TripListDialogStates.ADD_PROVIDE_DESCRIPTION)
async def _desc_provided(message: Message, state: FSMContext):
    user_trip_data[message.from_user.id]["desc"] = message.text
    await state.set_state(TripListDialogStates.ADD_PROVIDE_DATES)
    await message.answer("➕ <b>Add a trip: 3/3.</b>\n\n"
                         "Please specify dates of your trip in the following format:\n"
                         "<code>dd.mm.yy - dd.mm.yy</code>\n\n"
                         "For example: <code>02.04.24 - 12.04.24</code>",
                         reply_markup=cancel_keyboard)


@router.callback_query(F.data == "skip", TripListDialogStates.ADD_PROVIDE_DESCRIPTION)
async def _cancel_creation(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(TripListDialogStates.ADD_PROVIDE_DATES)
    await callback_query.message.answer("➕ <b>Add a trip: 3/3.</b>\n\n"
                                        "Please specify dates of your trip in the following format:\n"
                                        "<code>dd.mm.yy - dd.mm.yy</code>\n\n"
                                        "For example: <code>02.04.24 - 12.04.24</code>",
                                        reply_markup=cancel_keyboard)


@router.message(TripListDialogStates.ADD_PROVIDE_DATES)
async def _dates_provided(message: Message, state: FSMContext):
    try:
        start_date, end_date = DateFormatter.parse_date_pair(message.text)
    except ValueError as e:
        await commons.send_bad_input(message, e.args[0])
        return
    user_trip_data[message.from_user.id]["start"] = start_date
    user_trip_data[message.from_user.id]["end"] = end_date
    if message.from_user.id not in user_trip_data:
        await commons.send_error(message, "Cannot create your trip, repeat creation sequence")
    else:
        TripAccessor.create_trip(UserAccessor.convert_tg_user(message.from_user),
                                 user_trip_data[message.from_user.id])
        await state.set_state(TripListDialogStates.START)
        await message.answer("✅ <b>Trip successfully created.</b>")
        await init_dialog(message, state, message.from_user)
    del user_trip_data[message.from_user.id]


@router.callback_query(F.data.startswith("tr_"), TripListDialogStates.START)
async def _enter_trip(callback_query: CallbackQuery, state: FSMContext):
    await state.update_data(current_trip_id=int(callback_query.data[3:]))
    from bot.dialog import trip_detail_dialog
    await trip_detail_dialog.init_dialog(callback_query.message, state, callback_query.from_user)
