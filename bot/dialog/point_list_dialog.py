from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot.api.nominatim import NominatimAPI
from bot.data.accessor import TripAccessor, UserAccessor
from bot.data.formatter import DateFormatter
from bot.data.models import User
from bot.dialog import commons


class PointListDialogStates(StatesGroup):
    START = State()
    ADD_PROVIDE_NAME = State()
    ADD_SELECT_POINT = State()
    ADD_PROVIDE_DATES = State()


router = Router()
menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Add", callback_data="add")],
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
])
cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel_add")]
])
user_point_data = {}


def construct_keyboard(trip_id):
    points = TripAccessor.get_points_in_trip(trip_id)
    buttons = [[InlineKeyboardButton(text=f"{point.name}",
                                     callback_data=f"p_{point.get_id()}")]
               for point in points]
    return InlineKeyboardMarkup(inline_keyboard=buttons + menu_keyboard.inline_keyboard)


async def init_dialog(message: Message, state: FSMContext, user):
    await state.set_state(PointListDialogStates.START)
    data = await state.get_data()
    await message.answer("📍 <b>Trip points</b>",
                         reply_markup=construct_keyboard(data["current_trip_id"]))


@router.callback_query(F.data == "back", PointListDialogStates.START)
async def _go_back_btn(callback_query: CallbackQuery, state: FSMContext):
    from bot.dialog import trip_detail_dialog
    await trip_detail_dialog.init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "add", PointListDialogStates.START)
async def _add_btn(callback_query: CallbackQuery, state: FSMContext):
    user_point_data[callback_query.from_user.id] = {"name": None, "lat": None, "lon": None,
                                                    "osm_id": None, "city_name": None,
                                                    "city_id": None, "start": None,
                                                    "end": None, "osm_type": None}
    await state.set_state(PointListDialogStates.ADD_PROVIDE_NAME)
    await callback_query.message.answer("➕ <b>Add a trip point: 1/2.</b>\n\n"
                                        "Enter point name.",
                                        reply_markup=cancel_keyboard)


@router.callback_query(F.data == "cancel_add", PointListDialogStates.ADD_PROVIDE_NAME)
@router.callback_query(F.data == "cancel_add", PointListDialogStates.ADD_PROVIDE_DATES)
async def _cancel_creation(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("✖️ <b>Cancelled.</b>")
    await init_dialog(callback_query.message, state, callback_query.from_user)
    del user_point_data[callback_query.from_user.id]


@router.message(PointListDialogStates.ADD_PROVIDE_NAME)
async def _name_provided(message: Message, state: FSMContext):
    points = NominatimAPI.search(message.text)
    buttons = []
    places = []
    for i, point in enumerate(points):
        places.append(f"📍 <b>{i + 1}.</b> {point['display_name']} ({point['type']})")
        buttons.append([InlineKeyboardButton(
            text=f"{i + 1}.",
            callback_data=f"sel_{point['osm_type'][0].upper()}{point['osm_id']}"
        )])
    await state.set_state(PointListDialogStates.ADD_SELECT_POINT)
    await message.answer("➕ <b>Add a trip point: 1/2.</b>\n\n"
                         "Please select the specific point\n\n" +
                         "\n".join(places),
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("sel_"), PointListDialogStates.ADD_SELECT_POINT)
async def _point_selected(callback_query: CallbackQuery, state: FSMContext):
    osm_type = callback_query.data[4]
    osm_id = int(callback_query.data[5:])
    point = NominatimAPI.get_by_id(osm_id, osm_type)
    lat, lon = NominatimAPI.get_lat_lon_by_id(osm_id, osm_type)
    city = NominatimAPI.get_city_at_point(lat, lon)
    user_id = callback_query.from_user.id
    user_point_data[user_id]["name"] = NominatimAPI.get_name_in_answer(point)
    user_point_data[user_id]["city_name"] = NominatimAPI.get_name_in_answer(city)
    user_point_data[user_id]["city_id"] = city["osm_id"]
    user_point_data[user_id]["lat"] = lat
    user_point_data[user_id]["lon"] = lon
    user_point_data[user_id]["osm_id"] = osm_id
    user_point_data[user_id]["osm_type"] = osm_type
    await state.set_state(PointListDialogStates.ADD_PROVIDE_DATES)
    await callback_query.message.answer("➕ <b>Add a trip point: 2/2.</b>\n\n"
                                        "Please specify dates of your visit in the following format:\n"
                                        "<code>dd.mm.yy - dd.mm.yy</code>\n\n"
                                        "For example: <code>02.04.24 - 12.04.24</code>",
                                        reply_markup=cancel_keyboard)


@router.message(PointListDialogStates.ADD_PROVIDE_DATES)
async def _dates_provided(message: Message, state: FSMContext):
    try:
        start_date, end_date = DateFormatter.parse_date_pair(message.text)
    except ValueError as e:
        await commons.send_bad_input(message, e.args[0])
        return
    user_point_data[message.from_user.id]["start"] = start_date
    user_point_data[message.from_user.id]["end"] = end_date
    data = await state.get_data()
    if message.from_user.id not in user_point_data:
        await commons.send_error(message, "Cannot create your trip point, repeat creation sequence")
    else:
        TripAccessor.create_point(message.from_user,
                                  user_point_data[message.from_user.id],
                                  data["current_trip_id"])
        await state.set_state(PointListDialogStates.START)
        await message.answer("✅ <b>Trip point successfully created.</b>")
        await init_dialog(message, state, message.from_user)
    del user_point_data[message.from_user.id]


@router.callback_query(F.data.startswith("p_"), PointListDialogStates.START)
async def _enter_point(callback_query: CallbackQuery, state: FSMContext):
    await state.update_data(current_trip_point_id=int(callback_query.data[2:]))
    from bot.dialog import point_detail_dialog
    await point_detail_dialog.init_dialog(callback_query.message, state, callback_query.from_user)
