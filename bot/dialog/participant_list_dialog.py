from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot.data.models import User, Trip


class ParticipantListDialogStates(StatesGroup):
    START = State()
    CONFIRM_DELETE = State()


router = Router()
menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
])
confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🟢 Ok", callback_data="ok")],
    [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel")]
])


async def construct_keyboard(bot, state: FSMContext):
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    buttons = [[InlineKeyboardButton(text=f"{(await bot.get_chat(user.tg_id)).full_name}, {user.city_name}",
                                     callback_data=f"p_{user.get_id()}")]
               for user in trip.participants]
    return InlineKeyboardMarkup(inline_keyboard=buttons + menu_keyboard.inline_keyboard)


async def init_dialog(message: Message, state: FSMContext):
    await state.set_state(ParticipantListDialogStates.START)
    await message.answer("👥 <b>Trip participants.</b>\n"
                         "Click to remove from trip",
                         reply_markup=await construct_keyboard(message.bot, state))


@router.callback_query(F.data == "back", ParticipantListDialogStates.START)
async def _go_back_btn(callback_query: CallbackQuery, state: FSMContext):
    from bot.dialog import trip_detail_dialog
    await trip_detail_dialog.init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data.startswith("p_"), ParticipantListDialogStates.START)
async def _exclude_participant(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(ParticipantListDialogStates.CONFIRM_DELETE)
    await callback_query.message.answer("❌ <b>Are you sure you want to exclude this participant?</b>",
                                        reply_markup=confirm_keyboard)
    await state.update_data(removing_participant=int(callback_query.data[2:]))


@router.callback_query(F.data == "ok", ParticipantListDialogStates.CONFIRM_DELETE)
async def _confirm_delete(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    participant = User.get_by_id(data["removing_participant"])
    trip.participants.remove(participant)
    trip.save()
    await callback_query.message.answer("❌ <b>Participant excluded.</b>")
    del data["removing_participant"]
    await state.set_data(data)
    await init_dialog(callback_query.message, state)


@router.callback_query(F.data == "cancel", ParticipantListDialogStates.CONFIRM_DELETE)
async def _confirm_delete(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("✖️ <b>Cancelled.</b>")
    data = await state.get_data()
    del data["removing_participant"]
    await state.set_data(data)
    await init_dialog(callback_query.message, state)
