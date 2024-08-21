from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import F

from bot.api.nominatim import NominatimAPI
from bot.data.accessor import UserAccessor
from bot.data.models import INTEREST_TAGS
from bot.data.validator import validate_interests
from bot.dialog.commons import send_bad_input, send_warning, send_error


class RegisterDialogStates(StatesGroup):
    START = State()
    PROVIDE_LOCATION = State()
    PROVIDE_AGE = State()
    PROVIDE_GENDER = State()
    PROVIDE_INTERESTS = State()
    PROVIDE_BIO = State()


router = Router()
welcome_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Continue", callback_data="welcome_continue")]
])
provide_bio_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Skip", callback_data="skip_bio")]
])
finish_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Start my journey", url="/start")]
])
gender_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Male", callback_data="male"),
     InlineKeyboardButton(text="Female", callback_data="female")]
])
user_data = {}


async def init_dialog(message: Message, state: FSMContext):
    await state.set_state(RegisterDialogStates.START)
    await message.answer("👋 <b>Welcome to Travelagent bot.</b>\n\n"
                         "It seems like you use this bot only first "
                         "time, so let's setup a few parameters",
                         reply_markup=welcome_keyboard)


@router.callback_query(F.data == "welcome_continue", RegisterDialogStates.START)
async def query_welcome_continue(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(RegisterDialogStates.PROVIDE_LOCATION)
    await callback_query.message.answer("🚩 <b>Setup: 1/5.</b>\n\n"
                                        "Please provide your city.")
    user_data[callback_query.from_user.id] = {"city": None, "age": None, "bio": None,
                                              "interests": None, "gender": None}


@router.message(RegisterDialogStates.PROVIDE_LOCATION)
async def location_provided(message: Message, state: FSMContext):
    cities = NominatimAPI.get_possible_cities_by_name(message.text)
    if len(cities) == 0:
        await send_bad_input(message, "City not found. Please, try again")
    elif len(cities) > 1:
        await send_warning(message, "More than one city was found:\n" +
                           "\n".join(map(lambda x: f"• {x.full_name}", cities)) +
                           "\n\nPlease enter more specific name")
    else:
        await state.set_state(RegisterDialogStates.PROVIDE_AGE)
        await message.answer("🚩 <b>Setup: 2/5.</b>\n\n"
                             "Please provide your age.")
        user_data[message.from_user.id]["city"] = cities[0]


@router.message(RegisterDialogStates.PROVIDE_AGE)
async def age_provided(message: Message, state: FSMContext):
    if not message.text.isnumeric():
        await send_bad_input(message, "Bad age. Try again")
        return
    age = int(message.text)
    user_data[message.from_user.id]["age"] = age
    await state.set_state(RegisterDialogStates.PROVIDE_GENDER)
    await message.answer("🚩 <b>Setup: 3/5.</b>\n\n"
                         "Please select your gender.",
                         reply_markup=gender_keyboard)


@router.callback_query(RegisterDialogStates.PROVIDE_GENDER)
async def gender_provided(callback_query: CallbackQuery, state: FSMContext):
    user_data[callback_query.from_user.id]["gender"] = callback_query.data == "male"
    await state.set_state(RegisterDialogStates.PROVIDE_INTERESTS)
    await callback_query.message.answer("🚩 <b>Setup: 4/5.</b>\n\n"
                                        "Please provide your interests (each on new line). Choose "
                                        "from the list below.\n\n" +
                                        "\n".join(map(lambda x: f"<code>{x}</code>", INTEREST_TAGS)))


@router.message(RegisterDialogStates.PROVIDE_INTERESTS)
async def interests_provided(message: Message, state: FSMContext):
    if not validate_interests(message.text.strip()):
        await send_bad_input(message, "Bad interest list. Try again")
        return
    user_data[message.from_user.id]["interests"] = message.text.strip()
    await state.set_state(RegisterDialogStates.PROVIDE_BIO)
    await message.answer("🚩 <b>Setup: 5/5.</b>\n\n"
                         "Please provide your bio.",
                         reply_markup=provide_bio_keyboard)


async def handle_registration(user_id: int, message: Message, state: FSMContext) -> None:
    await state.clear()
    if user_id not in user_data:
        await send_error(message, "Cannot register you, repeat registration sequence")
    else:
        UserAccessor.register_user(user_id, user_data[user_id], message.from_user)
        await message.answer("✅ <b>Done.</b>\n\n"
                             "Your account is set up and you are ready to go.\n\n"
                             "Type /start again to start your journey!")
    del user_data[user_id]


@router.callback_query(F.data == "skip_bio", RegisterDialogStates.PROVIDE_BIO)
async def query_welcome_continue(callback_query: CallbackQuery, state: FSMContext):
    await handle_registration(callback_query.from_user.id, callback_query.message, state)


@router.message(RegisterDialogStates.PROVIDE_BIO)
async def bio_provided(message: Message, state: FSMContext):
    await handle_registration(message.from_user.id, message, state)
