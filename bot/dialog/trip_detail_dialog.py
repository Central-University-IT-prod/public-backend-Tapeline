import os
import uuid
from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputFile, FSInputFile

from bot.api.nominatim import NominatimAPI
from bot.api.openroute import RouteException
from bot.data.accessor import UserAccessor, TripAccessor
from bot.data.formatter import DateFormatter
from bot.data.models import Trip
from bot.dialog import commons
from bot.utils import route


class TripDetailDialogStates(StatesGroup):
    START = State()
    GENERATING_ROUTE = State()
    PARAMS = State()
    PARAMS_INPUT_NAME = State()
    PARAMS_INPUT_DESC = State()
    PARAMS_INPUT_DATES = State()
    PARAMS_INPUT_START = State()
    PARAMS_SELECT_START = State()
    PARAMS_CONFIRM_DELETE = State()
    INVITATION = State()


router = Router()
menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📍 Points", callback_data="points")],
    [InlineKeyboardButton(text="📝 Notes", callback_data="notes")],
    [InlineKeyboardButton(text="🧭 Route to start", callback_data="route"),
     InlineKeyboardButton(text="🧭 Full trip route", callback_data="full_route")],
    [InlineKeyboardButton(text="💳 Transactions", callback_data="transactions")],
    [InlineKeyboardButton(text="👥 Participants", callback_data="participants"),
     InlineKeyboardButton(text="🔖 Invitation", callback_data="invite")],
    [InlineKeyboardButton(text="⚙️ Parameters", callback_data="params")],
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
])
menu_part_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📍 Points", callback_data="points")],
    [InlineKeyboardButton(text="📝 Notes", callback_data="notes")],
    [InlineKeyboardButton(text="🧭 Route to start", callback_data="route"),
     InlineKeyboardButton(text="🧭 Full trip route", callback_data="full_route")],
    [InlineKeyboardButton(text="💳 Transactions", callback_data="transactions")],
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
])
param_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✏️ Change name", callback_data="c_name")],
    [InlineKeyboardButton(text="✏️ Change description", callback_data="c_desc")],
    [InlineKeyboardButton(text="✏️ Change dates of visit", callback_data="c_dates")],
    [InlineKeyboardButton(text="✏️ Change starting point", callback_data="c_start")],
    [InlineKeyboardButton(text="🗑️ Delete", callback_data="delete")],
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
])
cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel")]
])
confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🟢 Ok", callback_data="ok")],
    [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel")]
])
invitation_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔄 Regenerate invitation", callback_data="regen")],
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
])


async def create_trip_description(state: FSMContext):
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    start_point = NominatimAPI.get_something_at_point(trip.start_point_lat, trip.start_point_lon)
    return (f"✈️ <b>Your trip: {trip.name}.</b>\n"
            f"<code>{trip.start_date.strftime('%d.%m.%y')} - "
            f"{trip.end_date.strftime('%d.%m.%y')}</code>\n"
            f"{trip.description or 'No description'}\n"
            f"Starting point: {NominatimAPI.get_name_in_answer(start_point)}")


async def init_dialog(message: Message, state: FSMContext, user):
    await state.set_state(TripDetailDialogStates.START)
    desc = await create_trip_description(state)
    data = await state.get_data()
    if TripAccessor.is_owner(data["current_trip_id"], UserAccessor.convert_tg_user(user)):
        await message.answer(desc, reply_markup=menu_keyboard)
    else:
        await message.answer(desc, reply_markup=menu_part_keyboard)


async def init_params_dialog(message: Message, state: FSMContext):
    await state.set_state(TripDetailDialogStates.PARAMS)
    desc = await create_trip_description(state)
    await message.answer(desc, reply_markup=param_keyboard)


async def init_invitation_dialog(message: Message, state: FSMContext):
    await state.set_state(TripDetailDialogStates.INVITATION)
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    await message.answer("🔖 <b>Invitation management.</b>\n\n"
                         "Other users can join this trip, if they"
                         "enter /join-&lt;invitation_key&gt;.\n"
                         "Here you can manage this key.\n\n"
                         f"<u>Current invitation key:</u> <code>{trip.invitation}</code>\n"
                         f"<u>Current join command:</u> <code>/join-{trip.invitation}</code>",
                         reply_markup=invitation_keyboard)


@router.callback_query(F.data == "back", TripDetailDialogStates.START)
async def _back(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    del data["current_trip_id"]
    await state.set_data(data)
    from bot.dialog import trip_list_dialog
    await trip_list_dialog.init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "points", TripDetailDialogStates.START)
async def _points(callback_query: CallbackQuery, state: FSMContext):
    from bot.dialog import point_list_dialog
    await point_list_dialog.init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "participants", TripDetailDialogStates.START)
async def _participants(callback_query: CallbackQuery, state: FSMContext):
    from bot.dialog import participant_list_dialog
    await participant_list_dialog.init_dialog(callback_query.message, state)


@router.callback_query(F.data == "notes", TripDetailDialogStates.START)
async def _notes(callback_query: CallbackQuery, state: FSMContext):
    from bot.dialog import note_list_dialog
    await note_list_dialog.init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "transactions", TripDetailDialogStates.START)
async def _participants(callback_query: CallbackQuery, state: FSMContext):
    from bot.dialog import debt_list_dialog
    await debt_list_dialog.init_dialog(callback_query.message, state)


@router.callback_query(F.data == "route", TripDetailDialogStates.START)
async def _route(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("⏳ <b>Please wait, your route is being generated...</b>")
    await state.set_state(TripDetailDialogStates.GENERATING_ROUTE)
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    user = UserAccessor.convert_tg_user(callback_query.from_user)
    u_lat, u_lon = NominatimAPI.get_lat_lon_by_id(user.city_osm_id, user.city_osm_type)
    s_lat, s_lon = trip.start_point_lat, trip.start_point_lon
    try:
        result = route.create_route([u_lat, u_lon], [s_lat, s_lon])
    except RouteException as e:
        await commons.send_error(callback_query.message, e.args[0])
        await state.set_state(TripDetailDialogStates.START)
        return
    if result is None:
        await commons.send_error(callback_query.message, "Cannot create route: route too big or "
                                                         "has points that could not be connected "
                                                         "(e.g. over an ocean)")
        await state.set_state(TripDetailDialogStates.START)
        return
    photo = FSInputFile(result)
    await callback_query.message.answer_photo(photo)
    await state.set_state(TripDetailDialogStates.START)
    os.remove(result)


@router.callback_query(F.data == "full_route", TripDetailDialogStates.START)
async def _route(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("⏳ <b>Please wait, your route is being generated...</b>")
    await state.set_state(TripDetailDialogStates.GENERATING_ROUTE)
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    user = UserAccessor.convert_tg_user(callback_query.from_user)
    u_lat, u_lon = NominatimAPI.get_lat_lon_by_id(user.city_osm_id, user.city_osm_type)
    points = list(map(lambda x: (x.lat, x.lon), TripAccessor.get_points_in_trip(data["current_trip_id"])))
    points.insert(0, (trip.start_point_lat, trip.start_point_lon))
    points.insert(0, (u_lat, u_lon))
    points.append((u_lat, u_lon))
    try:
        result = route.create_poly_route(points)
    except RouteException as e:
        await commons.send_error(callback_query.message, e.args[0])
        await state.set_state(TripDetailDialogStates.START)
        return
    if result is None:
        await commons.send_error(callback_query.message, "Cannot create route: route too big or "
                                                         "has points that could not be connected "
                                                         "(e.g. over an ocean)")
        await state.set_state(TripDetailDialogStates.START)
        return
    photo = FSInputFile(result)
    await callback_query.message.answer_photo(photo)
    await state.set_state(TripDetailDialogStates.START)
    os.remove(result)


@router.callback_query(F.data == "params", TripDetailDialogStates.START)
async def _params(callback_query: CallbackQuery, state: FSMContext):
    await init_params_dialog(callback_query.message, state)


@router.callback_query(F.data == "cancel", TripDetailDialogStates.PARAMS_INPUT_DESC)
@router.callback_query(F.data == "cancel", TripDetailDialogStates.PARAMS_INPUT_DATES)
@router.callback_query(F.data == "cancel", TripDetailDialogStates.PARAMS_INPUT_NAME)
@router.callback_query(F.data == "cancel", TripDetailDialogStates.PARAMS_INPUT_START)
@router.callback_query(F.data == "cancel", TripDetailDialogStates.PARAMS_CONFIRM_DELETE)
async def _cancel(callback_query: CallbackQuery, state: FSMContext):
    await init_params_dialog(callback_query.message, state)


@router.callback_query(F.data == "c_name", TripDetailDialogStates.PARAMS)
async def _change_name(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(TripDetailDialogStates.PARAMS_INPUT_NAME)
    await callback_query.message.answer("✏️ <b>Change trip name.</b>\n\n"
                                        "Please provide new name",
                                        reply_markup=cancel_keyboard)


@router.callback_query(F.data == "c_desc", TripDetailDialogStates.PARAMS)
async def _change_desc(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(TripDetailDialogStates.PARAMS_INPUT_DESC)
    await callback_query.message.answer("✏️ <b>Change trip description.</b>\n\n"
                                        "Please provide new description",
                                        reply_markup=cancel_keyboard)


@router.callback_query(F.data == "c_dates", TripDetailDialogStates.PARAMS)
async def _change_name(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(TripDetailDialogStates.PARAMS_INPUT_DATES)
    await callback_query.message.answer("✏️ <b>Change trip dates.</b>\n\n"
                                        "Please specify new dates of your trip in the following format:\n"
                                        "<code>dd.mm.yy - dd.mm.yy</code>\n\n"
                                        "For example: <code>02.04.24 - 12.04.24</code>",
                                        reply_markup=cancel_keyboard)


@router.callback_query(F.data == "c_start", TripDetailDialogStates.PARAMS)
async def _change_start(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(TripDetailDialogStates.PARAMS_INPUT_START)
    await callback_query.message.answer("✏️ <b>Change trip start point.</b>\n\n"
                                        "Please specify new trip start point",
                                        reply_markup=cancel_keyboard)


@router.message(TripDetailDialogStates.PARAMS_INPUT_NAME)
async def _name_provided(message: Message, state: FSMContext):
    if Trip.select().where(Trip.name == message.text).exists():
        await commons.send_bad_input(message, "Trip name already occupied")
        return
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    trip.name = message.text
    trip.save()
    await init_params_dialog(message, state)


@router.message(TripDetailDialogStates.PARAMS_INPUT_DESC)
async def _desc_provided(message: Message, state: FSMContext):
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    trip.description = message.text
    trip.save()
    await init_params_dialog(message, state)


@router.message(TripDetailDialogStates.PARAMS_INPUT_DATES)
async def _dates_provided(message: Message, state: FSMContext):
    try:
        start_date, end_date = DateFormatter.parse_date_pair(message.text)
    except ValueError as e:
        await commons.send_bad_input(message, e.args[0])
        return
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    trip.start_date = start_date
    trip.end_date = end_date
    trip.save()
    await init_params_dialog(message, state)


@router.message(TripDetailDialogStates.PARAMS_INPUT_START)
async def _start_provided(message: Message, state: FSMContext):
    points = NominatimAPI.search(message.text)
    buttons = []
    places = []
    for i, point in enumerate(points):
        places.append(f"<b>{i + 1}.</b> {point['display_name']} ({point['type']})")
        buttons.append([InlineKeyboardButton(
            text=f"{i + 1}.",
            callback_data=f"sel_{point['osm_type'][0].upper()}{point['osm_id']}"
        )])
    await state.set_state(TripDetailDialogStates.PARAMS_SELECT_START)
    await message.answer("✏️ <b>Change trip start point.</b>\n\n"
                         "Please select specific start point\n\n" +
                         "\n".join(places),
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("sel_"), TripDetailDialogStates.PARAMS_SELECT_START)
async def _start_selected(callback_query: CallbackQuery, state: FSMContext):
    osm_type = callback_query.data[4]
    osm_id = int(callback_query.data[5:])
    lat, lon = NominatimAPI.get_lat_lon_by_id(osm_id, osm_type)
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    trip.start_point_lat = lat
    trip.start_point_lon = lon
    trip.save()
    await init_params_dialog(callback_query.message, state)


@router.callback_query(F.data == "delete", TripDetailDialogStates.PARAMS)
async def _delete(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(TripDetailDialogStates.PARAMS_CONFIRM_DELETE)
    await callback_query.message.answer("🗑️ <b>Are you sure you want to delete this trip?</b>",
                                        reply_markup=confirm_keyboard)


@router.callback_query(F.data == "ok", TripDetailDialogStates.PARAMS_CONFIRM_DELETE)
async def _confirm_delete(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    trip.delete_instance()
    await callback_query.message.answer("❌ <b>Trip deleted.</b>")
    del data["current_trip_id"]
    await state.set_data(data)
    from bot.dialog import trip_list_dialog
    await trip_list_dialog.init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "back", TripDetailDialogStates.PARAMS)
async def _back_from_params(callback_query: CallbackQuery, state: FSMContext):
    await init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "back", TripDetailDialogStates.INVITATION)
async def _back_from_invitations(callback_query: CallbackQuery, state: FSMContext):
    await init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "invite", TripDetailDialogStates.START)
async def _back_from_invitations(callback_query: CallbackQuery, state: FSMContext):
    await init_invitation_dialog(callback_query.message, state)


@router.callback_query(F.data == "regen", TripDetailDialogStates.INVITATION)
async def _regen_invitation(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(TripDetailDialogStates.INVITATION)
    data = await state.get_data()
    TripAccessor.regen_invitation(data["current_trip_id"])
    await callback_query.message.answer("✅ <b>Invitation key regenerated.</b>\n"
                                        "Old invitation key is now invalid")
    await init_invitation_dialog(callback_query.message, state)
