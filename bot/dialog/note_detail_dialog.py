import os
from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile

from bot.api.nominatim import NominatimAPI
from bot.data.accessor import TripAccessor, UserAccessor
from bot.data.models import User, Trip, TripPoint, Note
from bot.dialog import commons
from bot.utils import route


class NoteDetailDialogStates(StatesGroup):
    START = State()
    DELETE_CONFIRMATION = State()


router = Router()
menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")],
    [InlineKeyboardButton(text="👁️ Make public", callback_data="set_v_public"),
     InlineKeyboardButton(text="🔒 Make private", callback_data="set_v_private")],
    [InlineKeyboardButton(text="🗑️ Delete", callback_data="delete")]
])
menu_viewer_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
])
confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🟢 Ok", callback_data="ok")],
    [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel")]
])


async def init_dialog(message: Message, state: FSMContext, user):
    await state.set_state(NoteDetailDialogStates.START)
    data = await state.get_data()
    note = Note.get_by_id(data["current_note_id"])
    for m_id in map(int, note.tg_message_ids.split()):
        await message.bot.forward_message(message.chat.id, note.tg_chat_id, m_id)
    if UserAccessor.convert_tg_user(user) == note.owner:
        await message.answer(f"📝 <b>Trip note: {'👁️' if note.is_public else '🔒'} {note.name}.</b>\n",
                             reply_markup=menu_keyboard)
    else:
        await message.answer(f"📝 <b>Trip note: {'👁️' if note.is_public else '🔒'} {note.name}.</b>\n",
                             reply_markup=menu_viewer_keyboard)


@router.callback_query(F.data == "delete", NoteDetailDialogStates.START)
async def _delete(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(NoteDetailDialogStates.DELETE_CONFIRMATION)
    await callback_query.message.answer("🗑️ <b>Are you sure you want to delete this note?</b>",
                                        reply_markup=confirm_keyboard)


@router.callback_query(F.data == "cancel", NoteDetailDialogStates.DELETE_CONFIRMATION)
async def _cancel_delete(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("✖️ <b>Deletion cancelled.</b>")
    await init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "ok", NoteDetailDialogStates.DELETE_CONFIRMATION)
async def _confirm_delete(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    note = Note.get_by_id(data["current_note_id"])
    note.delete_instance()
    await callback_query.message.answer("❌ <b>Note deleted.</b>")
    del data["current_note_id"]
    await state.set_data(data)
    from bot.dialog import note_list_dialog
    await note_list_dialog.init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "back", NoteDetailDialogStates.START)
async def _back(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    del data["current_note_id"]
    await state.set_data(data)
    from bot.dialog import note_list_dialog
    await note_list_dialog.init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "set_v_public", NoteDetailDialogStates.START)
async def _set_public(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    note = Note.get_by_id(data["current_note_id"])
    note.is_public = True
    note.save()
    await callback_query.message.answer("👁️ <b>Note made public.</b>")


@router.callback_query(F.data == "set_v_private", NoteDetailDialogStates.START)
async def _set_private(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    note = Note.get_by_id(data["current_note_id"])
    note.is_public = False
    note.save()
    await callback_query.message.answer("🔒 <b>Note made private.</b>")
