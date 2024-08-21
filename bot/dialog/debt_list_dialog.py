from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot.data.accessor import DebtAccessor, UserAccessor
from bot.data.models import User, Trip, Debt
from bot.dialog import commons


class DebtListDialogStates(StatesGroup):
    START = State()
    MY_DEBTS = State()
    MY_CREDITS = State()
    CREATING_TRANSACTION = State()


router = Router()
menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💳 My debts", callback_data="debts"),
     InlineKeyboardButton(text="💳 My credits", callback_data="credits")],
    [InlineKeyboardButton(text="➕ Create new transaction", callback_data="new")],
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
])
confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🟢 Ok", callback_data="ok")],
    [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel")]
])
back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
])
transaction_user_data = {}


async def get_user_names_by_tg_id(bot, tg_id):
    full_name = (await bot.get_chat(tg_id)).full_name
    username = UserAccessor.convert_tg_id_user(tg_id).tg_username
    if username is not None:
        return f"@{username}"
    else:
        return full_name


async def init_dialog(message: Message, state: FSMContext):
    await state.set_state(DebtListDialogStates.START)
    await message.answer("💳 <b>Transactions and debts</b>",
                         reply_markup=menu_keyboard)


@router.callback_query(F.data == "back", DebtListDialogStates.START)
async def _go_back_btn(callback_query: CallbackQuery, state: FSMContext):
    from bot.dialog import trip_detail_dialog
    await trip_detail_dialog.init_dialog(callback_query.message, state, callback_query.from_user)


@router.callback_query(F.data == "back", DebtListDialogStates.MY_DEBTS)
@router.callback_query(F.data == "back", DebtListDialogStates.MY_CREDITS)
@router.callback_query(F.data == "cancel", DebtListDialogStates.CREATING_TRANSACTION)
async def _go_back_from_lists_btn(callback_query: CallbackQuery, state: FSMContext):
    await init_dialog(callback_query.message, state)


@router.callback_query(F.data == "debts", DebtListDialogStates.START)
async def _debts(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(DebtListDialogStates.MY_DEBTS)
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    user = UserAccessor.convert_tg_user(callback_query.from_user)
    debts_amount, debts = DebtAccessor.total_debts_amount(trip, user)
    text = (f"💳 <b>Your debts.</b>\n\n"
            f"Total: {debts_amount}\n\n")
    texts = []
    for x in debts:
        texts.append(f"{x.amount} to {await get_user_names_by_tg_id(callback_query.bot, x.recipient.tg_id)}")
    await callback_query.message.answer(text + "\n".join(texts), reply_markup=back_keyboard)


@router.callback_query(F.data == "credits", DebtListDialogStates.START)
async def _credits(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(DebtListDialogStates.MY_CREDITS)
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    user = UserAccessor.convert_tg_user(callback_query.from_user)
    credits_amount, credits_records = DebtAccessor.total_settlement_amount(trip, user)
    text = (f"💳 <b>Your credits.</b>\n\n"
            f"Total: {credits_amount}\n"
            f"Click to settle")
    buttons = [[InlineKeyboardButton(text=f"{x.amount} from "
                                          f"{await get_user_names_by_tg_id(callback_query.bot, x.debtor.tg_id)}",
                                     callback_data=f"stl_{x.get_id()}")]
               for x in credits_records] + back_keyboard.inline_keyboard
    await callback_query.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("stl_"), DebtListDialogStates.MY_CREDITS)
async def _settle(callback_query: CallbackQuery, state: FSMContext):
    debt = Debt.get_by_id(int(callback_query.data[4:]))
    debt.delete_instance()
    await callback_query.message.answer("✅ <b>Debt settled.</b>")
    await init_dialog(callback_query.message, state)


async def construct_participant_keyboard(bot, state: FSMContext, user):
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    buttons = [[InlineKeyboardButton(text=f"{await get_user_names_by_tg_id(bot, user.tg_id)}, "
                                          f"{user.city_name}",
                                     callback_data=f"p_{user.get_id()}")]
               for user in list(filter(lambda x: x != user, list(trip.participants) + [trip.owner]))]
    buttons.extend([
        [InlineKeyboardButton(text="🟠 Cancel", callback_data="cancel")]
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "new", DebtListDialogStates.START)
async def _new_transaction(callback_query: CallbackQuery, state: FSMContext):
    transaction_user_data[callback_query.from_user.id] = {"users": [], "amount": None}
    user = UserAccessor.convert_tg_user(callback_query.from_user)
    await state.set_state(DebtListDialogStates.CREATING_TRANSACTION)
    await callback_query.message.answer("➕ <b>New transaction.</b>\n\n"
                                        "Please select debtors. Then enter amount in chat",
                                        reply_markup=await construct_participant_keyboard(callback_query.bot,
                                                                                          state,
                                                                                          user))


@router.callback_query(F.data.startswith("p_"), DebtListDialogStates.CREATING_TRANSACTION)
async def _add_user(callback_query: CallbackQuery, state: FSMContext):
    user = User.get_by_id(int(callback_query.data[2:]))
    transaction_user_data[callback_query.from_user.id]["users"].append(user)
    await callback_query.message.answer(f"{await get_user_names_by_tg_id(callback_query.bot, user.tg_id)} selected")


@router.message(DebtListDialogStates.CREATING_TRANSACTION)
async def _entered_amount(message: Message, state: FSMContext):
    if not message.text.isnumeric():
        await commons.send_bad_input(message, "Amount must be a number")
        return
    data = await state.get_data()
    trip = Trip.get_by_id(data["current_trip_id"])
    debtors = transaction_user_data[message.from_user.id]["users"]
    per_user_amount = float(message.text) / len(debtors)
    user_name = await get_user_names_by_tg_id(message.bot, message.from_user.id)
    for debtor in debtors:
        await message.bot.send_message(debtor.tg_id, f"<b>You now owe {per_user_amount} to {user_name}</b>")
    DebtAccessor.create_debt(
        trip,
        UserAccessor.convert_tg_user(message.from_user),
        float(message.text),
        debtors
    )
    del transaction_user_data[message.from_user.id]
    await message.answer("✅ <b>Transaction created.</b>")
    await init_dialog(message, state)
