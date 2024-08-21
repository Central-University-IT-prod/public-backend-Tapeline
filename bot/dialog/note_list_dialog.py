from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot.api.nominatim import NominatimAPI
from bot.data.accessor import TripAccessor, UserAccessor, NoteAccessor
from bot.data.models import User, Trip, TripPoint, Note
from bot.dialog import commons


class NoteListDialogStates(StatesGroup):
    START = State()
    ADD_PROVIDE_NAME = State()
    ADD_UPLOAD_DATA = State()
    ADD_SET_VISIBILITY = State()


router = Router()
menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Add", callback_data="add")],
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
])
cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel_add")]
])
cancel_done_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Done", callback_data="done")],
    [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel_add")]
])
visibility_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👁️ Public", callback_data="vis_public"),
     InlineKeyboardButton(text="🔒 Private", callback_data="vis_private")],
    [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel_add")]
])
user_note_data = {}


def construct_keyboard(user: User, trip_id):
    notes = NoteAccessor.get_notes_for_user(trip_id, user.get_id())
    buttons = [[InlineKeyboardButton(text=f"{'👑 ' if note.owner == user else ''}"
                                          f"{'👁️' if note.is_public else '🔒'} {note.name}",
                                     callback_data=f"n_{note.get_id()}")]
               for note in notes]
    return InlineKeyboardMarkup(inline_keyboard=buttons + menu_keyboard.inline_keyboard)


async def init_dialog(message: Message, state: FSMContext, user):
    await state.set_state(NoteListDialogStates.START)
    data = await state.get_data()
    await message.answer("📝 <b>Trip notes.</b>",
                         reply_markup=construct_keyboard(UserAccessor.convert_tg_user(user),
                                                         data["current_trip_id"]))


@router.callback_query(F.data == "back", NoteListDialogStates.START)
async def _go_back_btn(callback_query: CallbackQuery, state: FSMContext):
    from bot.dialog import trip_detail_dialog
    await trip_detail_dialog.init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "add", NoteListDialogStates.START)
async def _add_btn(callback_query: CallbackQuery, state: FSMContext):
    user_note_data[callback_query.from_user.id] = {"name": None, "messages": [], "is_public": None,
                                                   "chat": callback_query.message.chat.id}
    await state.set_state(NoteListDialogStates.ADD_PROVIDE_NAME)
    await callback_query.message.answer("➕ <b>Add a trip note: 1/3.</b>\n\n"
                                        "Enter note name.",
                                        reply_markup=cancel_keyboard)


@router.callback_query(F.data == "cancel_add", NoteListDialogStates.ADD_UPLOAD_DATA)
@router.callback_query(F.data == "cancel_add", NoteListDialogStates.ADD_PROVIDE_NAME)
@router.callback_query(F.data == "cancel_add", NoteListDialogStates.ADD_SET_VISIBILITY)
async def _cancel_creation(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("✖️ <b>Cancelled.</b>")
    await init_dialog(callback_query.message, state, callback_query.from_user)
    del user_note_data[callback_query.from_user.id]


@router.message(NoteListDialogStates.ADD_PROVIDE_NAME)
async def _name_provided(message: Message, state: FSMContext):
    user_note_data[message.from_user.id]["name"] = message.text
    await state.set_state(NoteListDialogStates.ADD_UPLOAD_DATA)
    await message.answer("➕ <b>Add a trip note: 2/3.</b>\n\n"
                         "Specify the content of your note. You can send whatever you want: text, "
                         "videos, images, other media. When you are done, press 'Done' button.",
                         reply_markup=cancel_done_keyboard)


@router.message(NoteListDialogStates.ADD_UPLOAD_DATA)
async def _upload(message: Message, state: FSMContext):
    user_note_data[message.from_user.id]["messages"].append(message.message_id)


@router.callback_query(F.data == "done", NoteListDialogStates.ADD_UPLOAD_DATA)
async def _upload_completed(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(NoteListDialogStates.ADD_SET_VISIBILITY)
    await callback_query.message.answer("➕ <b>Add a trip note: 3/3.</b>\n\n"
                                        "Specify visibility settings:",
                                        reply_markup=visibility_keyboard)


@router.callback_query(F.data.startswith("vis_"), NoteListDialogStates.ADD_SET_VISIBILITY)
async def _visibility_selected(callback_query: CallbackQuery, state: FSMContext):
    user_note_data[callback_query.from_user.id]["is_public"] = callback_query.data == "vis_public"
    data = await state.get_data()
    if callback_query.from_user.id not in user_note_data:
        await commons.send_error(callback_query.message,
                                 "Cannot create your trip note, repeat creation sequence")
    else:
        NoteAccessor.create_note(callback_query.from_user,
                                 user_note_data[callback_query.from_user.id],
                                 data["current_trip_id"])
        await state.set_state(NoteListDialogStates.START)
        await callback_query.message.answer("✅ <b>Note successfully created.</b>")
        await init_dialog(callback_query.message, state, callback_query.from_user)
    del user_note_data[callback_query.from_user.id]


@router.callback_query(F.data.startswith("n_"), NoteListDialogStates.START)
async def _enter_point(callback_query: CallbackQuery, state: FSMContext):
    await state.update_data(current_note_id=int(callback_query.data[2:]))
    from bot.dialog import note_detail_dialog
    await note_detail_dialog.init_dialog(callback_query.message, state, callback_query.from_user)
