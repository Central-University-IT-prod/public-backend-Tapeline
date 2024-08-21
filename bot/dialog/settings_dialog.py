import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot.api.nominatim import NominatimAPI
from bot.data.accessor import UserAccessor
from bot.data.models import INTEREST_TAGS
from bot.data.validator import validate_interests
from bot.dialog import commons


class SettingsDialogStates(StatesGroup):
    START = State()
    PARAMS_INPUT_BIO = State()
    PARAMS_INPUT_CITY = State()
    PARAMS_INPUT_INTERESTS = State()
    PARAMS_SELECT_CITY = State()
    PARAMS_CONFIRM_DELETE = State()


router = Router()
param_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✏️ Change city", callback_data="c_city"),
     InlineKeyboardButton(text="✏️ Change bio", callback_data="c_bio"),
     InlineKeyboardButton(text="✏️ Change interests", callback_data="c_interests")],
    [InlineKeyboardButton(text="👁️ Display me in 'Explore'", callback_data="set_public"),
     InlineKeyboardButton(text="🔒 Do not isplay me in 'Explore'", callback_data="set_private")],
    [InlineKeyboardButton(text="🗑️ Delete account", callback_data="delete")],
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
])
cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel")]
])
confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🗑️ Yes, I want", callback_data="ok")],
    [InlineKeyboardButton(text="🟢 No, I don't want", callback_data="cancel")]
])


def create_profile_description(tg_user):
    user = UserAccessor.convert_tg_user(tg_user)
    return (f"👤 <b>Profile settings.</b>\n\n"
            f"<u>Age:</u> <code>{datetime.date.today().year - user.year_of_birth}</code>\n"
            f"<u>Gender:</u> <code>{'Male' if user.gender else 'Female'}</code>\n"
            f"<u>Bio:</u> <pre>{str(user.bio)}</pre>\n"
            f"<u>Home city/town:</u> <code>{user.city_name}</code>\n"
            f"<u>Are you listed in 'Explore travellers'?</u> "
            f"<code>{'Yes' if user.display_in_explore else 'No'}</code>\n"
            f"<u>Interests:</u> " + ", ".join(map(lambda x: f"<code>{x}</code>",
                                                  user.interests.split("\n"))))


async def init_dialog(message: Message, state: FSMContext, user):
    await state.set_state(SettingsDialogStates.START)
    await message.answer(create_profile_description(user), reply_markup=param_keyboard)


@router.callback_query(F.data == "back", SettingsDialogStates.START)
async def _back(callback_query: CallbackQuery, state: FSMContext):
    from bot.dialog import main_menu_dialog
    await main_menu_dialog.init_dialog(callback_query.message, state)


@router.callback_query(F.data == "cancel", SettingsDialogStates.PARAMS_INPUT_BIO)
@router.callback_query(F.data == "cancel", SettingsDialogStates.PARAMS_INPUT_CITY)
@router.callback_query(F.data == "cancel", SettingsDialogStates.PARAMS_SELECT_CITY)
@router.callback_query(F.data == "cancel", SettingsDialogStates.PARAMS_CONFIRM_DELETE)
async def _cancel(callback_query: CallbackQuery, state: FSMContext):
    await init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "c_bio", SettingsDialogStates.START)
async def _change_bio(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsDialogStates.PARAMS_INPUT_BIO)
    await callback_query.message.answer("✏️ <b>Change your bio.</b>\n\n"
                                        "Please provide new bio",
                                        reply_markup=cancel_keyboard)


@router.callback_query(F.data == "c_city", SettingsDialogStates.START)
async def _change_city(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsDialogStates.PARAMS_INPUT_CITY)
    await callback_query.message.answer("✏️ <b>Change your home city.</b>\n\n"
                                        "Please specify new home city",
                                        reply_markup=cancel_keyboard)


@router.callback_query(F.data == "c_interests", SettingsDialogStates.START)
async def _change_city(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsDialogStates.PARAMS_INPUT_INTERESTS)
    await callback_query.message.answer("✏️ <b>Change your interests.</b>\n\n"
                                        "Please provide your interests (each on new line). Choose "
                                        "from the list below.\n\n" +
                                        "\n".join(map(lambda x: f"<code>{x}</code>", INTEREST_TAGS)),
                                        reply_markup=cancel_keyboard)


@router.message(SettingsDialogStates.PARAMS_INPUT_INTERESTS)
async def _interests_provided(message: Message, state: FSMContext):
    if not validate_interests(message.text.strip()):
        await commons.send_bad_input(message, "Bad interest list. Try again")
        return
    user = UserAccessor.convert_tg_user(message.from_user)
    user.interests = message.text.strip()
    user.save()
    await init_dialog(message, state, message.from_user)


@router.message(SettingsDialogStates.PARAMS_INPUT_BIO)
async def _bio_provided(message: Message, state: FSMContext):
    user = UserAccessor.convert_tg_user(message.from_user)
    user.bio = message.text
    user.save()
    await init_dialog(message, state, message.from_user)


@router.message(SettingsDialogStates.PARAMS_INPUT_CITY)
async def _city_provided(message: Message, state: FSMContext):
    cities = NominatimAPI.get_possible_cities_by_name(message.text)
    if len(cities) == 0:
        await commons.send_bad_input(message, "City not found. Please, try again")
    elif len(cities) > 1:
        await commons.send_warning(message, "More than one city was found:\n" +
                                   "\n".join(map(lambda x: f"• {x.full_name}", cities)) +
                                   "\n\nPlease enter more specific name")
    else:
        user = UserAccessor.convert_tg_user(message.from_user)
        user.city_osm_id = cities[0].id
        user.city_osm_type = cities[0].type
        user.city_name = cities[0].name
        user.save()
    await init_dialog(message, state, message.from_user)


@router.callback_query(F.data == "delete", SettingsDialogStates.START)
async def _delete(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsDialogStates.PARAMS_CONFIRM_DELETE)
    await callback_query.message.answer("⚠️ <b>WARNING!</b>\n\n"
                                        "You're about to delete your Travelagent account.\n\n"
                                        "This means that all trips and notes that you own "
                                        "will be irrecoverably lost once you complete deletion.\n\n"
                                        "<b>Do you REALLY want to proceed?</b>",
                                        reply_markup=confirm_keyboard)


@router.callback_query(F.data == "ok", SettingsDialogStates.PARAMS_CONFIRM_DELETE)
async def _confirm_delete(callback_query: CallbackQuery, state: FSMContext):
    user = UserAccessor.convert_tg_user(callback_query.from_user)
    user.delete_instance()
    await callback_query.message.answer("❎ <b>Account successfully deleted.</b>")


@router.callback_query(F.data == "set_public", SettingsDialogStates.START)
async def _set_public(callback_query: CallbackQuery, state: FSMContext):
    user = UserAccessor.convert_tg_user(callback_query.from_user)
    user.display_in_explore = True
    user.save()
    await callback_query.message.answer("👁️ <b>Profile made public.</b>")


@router.callback_query(F.data == "set_private", SettingsDialogStates.START)
async def _set_private(callback_query: CallbackQuery, state: FSMContext):
    user = UserAccessor.convert_tg_user(callback_query.from_user)
    user.display_in_explore = False
    user.save()
    await callback_query.message.answer("🔒 <b>Profile made private.</b>")
