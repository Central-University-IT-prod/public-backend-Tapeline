import os

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile

from bot.api.nominatim import NominatimAPI
from bot.api.openmeteo import OpenMeteoAPI
from bot.api.openroute import RouteException
from bot.api.opentrip import OpenTripMapAPI
from bot.data.accessor import TripAccessor
from bot.data.models import Trip, TripPoint
from bot.dialog import commons
from bot.utils import route
from bot.utils.date import datetime_range


class PointDetailDialogStates(StatesGroup):
    START = State()
    DELETE_CONFIRMATION = State()
    GENERATING_ROUTE = State()


router = Router()
menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")],
    [InlineKeyboardButton(text="🧭 See route", callback_data="route")],
    [InlineKeyboardButton(text="🚩 List interesting places around", callback_data="places")],
    [InlineKeyboardButton(text="🍗 List public catering around", callback_data="food")],
    [InlineKeyboardButton(text="🏠 List accommodations around", callback_data="accommodation")],
    [InlineKeyboardButton(text="🗑️ Delete", callback_data="delete")]
])
confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🟢 Ok", callback_data="ok")],
    [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel")]
])


def get_forecast_for_point(point):
    date_range = list(datetime_range(point.start_date, point.end_date))
    date_range = list(map(lambda x: x.strftime("%Y-%m-%d"), date_range))
    forecast = OpenMeteoAPI.forecast_for_dates(point.lat, point.lon, date_range)
    return OpenMeteoAPI.format_forecast(forecast)


async def init_dialog(message: Message, state: FSMContext, user):
    await state.set_state(PointDetailDialogStates.START)
    data = await state.get_data()
    point = TripPoint.get_by_id(data["current_trip_point_id"])
    forecast = get_forecast_for_point(point)
    await message.answer(f"📍 <b>Trip point: {point.name} ({point.city_name}).</b>\n"
                         f"<u>Dates:</u> <code>{point.start_date.strftime('%d.%m.%y')} - "
                         f"{point.end_date.strftime('%d.%m.%y')}</code>\n\n"
                         f"🌦 Forecast for dates of visit (maximum range possible: 16 days from now):\n" +
                         "\n".join(map(lambda x: f"<code>{x[0][5:]}</code> - "
                                                 f"{x[1][1]} {x[1][0]} "
                                                 f"{x[2]} - {x[3]}", forecast)),
                         reply_markup=menu_keyboard)


@router.callback_query(F.data == "delete", PointDetailDialogStates.START)
async def _delete(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(PointDetailDialogStates.DELETE_CONFIRMATION)
    await callback_query.message.answer("🗑️ <b>Are you sure you want to delete this point?</b>",
                                        reply_markup=confirm_keyboard)


@router.callback_query(F.data == "cancel", PointDetailDialogStates.DELETE_CONFIRMATION)
async def _cancel_delete(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("✖️ <b>Deletion cancelled.</b>")
    await init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "ok", PointDetailDialogStates.DELETE_CONFIRMATION)
async def _confirm_delete(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    TripAccessor.remove_point(data["current_trip_point_id"], data["current_trip_id"])
    await callback_query.message.answer("❌ <b>Point deleted.</b>")
    del data["current_trip_point_id"]
    await state.set_data(data)
    from bot.dialog import point_list_dialog
    await point_list_dialog.init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "route", PointDetailDialogStates.START)
async def _route(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("⏳ <b>Please wait, your route is being generated...</b>")
    await state.set_state(PointDetailDialogStates.GENERATING_ROUTE)
    data = await state.get_data()
    prev = TripAccessor.get_prev_point_lat_lon(data["current_trip_id"], data["current_trip_point_id"])
    current = TripPoint.get_by_id(data["current_trip_point_id"])
    try:
        result = route.create_route(prev, [current.lat, current.lon])
    except RouteException as e:
        await commons.send_error(callback_query.message, e.args[0])
        await state.set_state(PointDetailDialogStates.START)
        return
    if result is None:
        await commons.send_error(callback_query.message, "Cannot create route: route too big or "
                                                         "has points that could not be connected "
                                                         "(e.g. over an ocean)")
        await state.set_state(PointDetailDialogStates.START)
        return
    photo = FSInputFile(result)
    await callback_query.message.answer_photo(photo)
    await state.set_state(PointDetailDialogStates.START)
    os.remove(result)


def format_feature(feature):
    place = NominatimAPI.get_by_id(int(feature.xid[1:]), feature.xid[0])
    if place is not None:
        address = NominatimAPI.get_address(place)
    else:
        address = "address not found"
    if feature.osm_link is not None:
        return f"{OpenTripMapAPI.get_icons_for_feature(feature)} " + \
               f"<a href=\"https://www.openstreetmap.org/{feature.osm_link}\">" + \
               f"{feature.name}</a> ({address})"
    else:
        return f"{OpenTripMapAPI.get_icons_for_feature(feature)} " + \
            f"{feature.name} ({address})"


def format_other_features(feature):
    place = NominatimAPI.get_by_id(int(feature.xid[1:]), feature.xid[0])
    if place is not None:
        address = NominatimAPI.get_address(place)
    else:
        address = "address not found"
    if feature.osm_link is not None:
        return f"<a href=\"https://www.openstreetmap.org/{feature.osm_link}\">" + \
               f"{feature.name}</a> ({address})"
    else:
        return f"{feature.name} ({address})"


@router.callback_query(F.data == "places", PointDetailDialogStates.START)
async def _places(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    point = TripPoint.get_by_id(data["current_trip_point_id"])
    places = OpenTripMapAPI.get_places_around(point.lat, point.lon, radius=8000)
    places = OpenTripMapAPI.filter_suitable(places)
    places = OpenTripMapAPI.sort_by_relevancy(places, radius=8000)
    places = places[:min(15, len(places))]
    places_formatted = list(map(format_feature, places))
    if len(places_formatted) == 0:
        await callback_query.message.answer("🚩 <b>Interesting places not found.</b>")
    else:
        await callback_query.message.answer("🚩 <b>Interesting places around.</b>\n\n" +
                                            "\n".join(places_formatted))


@router.callback_query(F.data == "food", PointDetailDialogStates.START)
async def _food(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer("Please wait. This can take a while")
    data = await state.get_data()
    point = TripPoint.get_by_id(data["current_trip_point_id"])
    places = OpenTripMapAPI.get_foods_around(point.lat, point.lon, radius=8000)
    places = OpenTripMapAPI.sort_by_relevancy(places, radius=8000)
    places = places[:min(15, len(places))]
    places_formatted = list(map(format_other_features, places))
    if len(places_formatted) == 0:
        await callback_query.message.answer("🍗 <b>Public catering not found.</b>")
    else:
        await callback_query.message.answer("🍗 <b>Public catering around.</b>\n\n" +
                                            "\n".join(places_formatted))


@router.callback_query(F.data == "accommodation", PointDetailDialogStates.START)
async def _accommodation(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer("Please wait. This can take a while")
    data = await state.get_data()
    point = TripPoint.get_by_id(data["current_trip_point_id"])
    places = OpenTripMapAPI.get_accommodations_around(point.lat, point.lon, radius=8000)
    places = OpenTripMapAPI.sort_by_relevancy(places, radius=8000)
    places = places[:min(15, len(places))]
    places_formatted = list(map(format_other_features, places))
    if len(places_formatted) == 0:
        await callback_query.message.answer("🏠 <b>Accommodations not found.</b>")
    else:
        await callback_query.message.answer("🏠 <b>Accommodations around.</b>\n\n" +
                                            "\n".join(places_formatted))


@router.callback_query(F.data == "back", PointDetailDialogStates.START)
async def _back(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    del data["current_trip_point_id"]
    await state.set_data(data)
    from bot.dialog import point_list_dialog
    await point_list_dialog.init_dialog(callback_query.message, state, callback_query.from_user)
