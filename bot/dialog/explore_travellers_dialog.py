from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot.api.nominatim import NominatimAPI
from bot.data.accessor import UserAccessor
from bot.data.models import User, Trip
from bot.data.user_recommendation import UserRecommendation


class ExploreDialogStates(StatesGroup):
    START = State()
    PRIVATE_MESSAGE = State()


router = Router()
menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
])
cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel")]
])


def get_location(user):
    city = NominatimAPI.get_by_id(user.city_osm_id, user.city_osm_type)
    return f"{NominatimAPI.get_name_in_answer(city)}, {city['address']['country']}"


def construct_keyboard_and_message(user):
    rec = UserRecommendation.list_recommended_users(
        #user, list(User.select().where(User.tg_username is not None))  # not working ?
        user, list(filter(lambda x: x.tg_username is not None, list(User.select())))
    )
    text = [f"{'👨' if user.gender else '👩'} "
            f"@{user.tg_username}, "
            f"{UserAccessor.get_age(user)}, "
            f"{'Male' if user.gender else 'Female'}, "
            f"{get_location(user)}\n"
            f"<pre>{user.bio if user.bio is not None else 'No bio'}</pre>\n"
            f"Interests: " + ", ".join(map(lambda x: f"<code>{x}</code>",
                                           user.interests.split("\n")))
            for user in rec]
    text = "\n\n".join(text)
    if len(rec) == 0:
        text = "No recommendations for now"
    buttons = [[InlineKeyboardButton(text=f"@{user.tg_username}",
                                     callback_data=f"pm_{user.get_id()}")]
               for user in rec]
    return text, InlineKeyboardMarkup(inline_keyboard=buttons + menu_keyboard.inline_keyboard)


async def init_dialog(message: Message, state: FSMContext, user):
    await state.set_state(ExploreDialogStates.START)
    text, kb = construct_keyboard_and_message(UserAccessor.convert_tg_user(user))
    await message.answer("👥 <b>Explore travellers.</b>\n"
                         "Here you can explore travellers that are sharing interests with you.\n"
                         "Click a user to send a private notification to him.\n\n" + text,
                         reply_markup=kb)


@router.callback_query(F.data == "back", ExploreDialogStates.START)
async def _go_back_btn(callback_query: CallbackQuery, state: FSMContext):
    from bot.dialog import main_menu_dialog
    await main_menu_dialog.init_dialog(callback_query.message, state)


@router.callback_query(F.data.startswith("pm_"), ExploreDialogStates.START)
async def _exclude_participant(callback_query: CallbackQuery, state: FSMContext):
    user = User.get_by_id(int(callback_query.data[3:]))
    await state.set_state(ExploreDialogStates.PRIVATE_MESSAGE)
    await callback_query.message.answer(f"📨 <b>Sending private notification to @{user.tg_username}.</b>\n"
                                        f"Provide content of your notification (E.g. you can write your"
                                        f"username for {user.tg_username} to answer)",
                                        reply_markup=cancel_keyboard)
    await state.update_data(notifying=int(callback_query.data[3:]))


@router.message(ExploreDialogStates.PRIVATE_MESSAGE)
async def _send(message: Message, state: FSMContext):
    data = await state.get_data()
    user = User.get_by_id(data["notifying"])
    await message.bot.send_message(user.tg_id, f"📭 @{message.from_user.username} reached you!\n\n"
                                               f"@{message.from_user.username} wants to speak to you:\n"
                                               f"<pre>{message.text}</pre>")
    await message.answer("✅ <b>Notification sent.</b>")
    del data["notifying"]
    await state.set_data(data)
    await init_dialog(message, state, message.from_user)
