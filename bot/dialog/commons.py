from aiogram.types import Message


async def send_bad_input(message: Message, text: str) -> None:
    await message.answer(f"❌ <b>Invalid input.</b>\n\n{text}")


async def send_error(message: Message, text: str) -> None:
    await message.answer(f"❌ <b>Error.</b>\n\n{text}")


async def send_warning(message: Message, text: str) -> None:
    await message.answer(f"⚠️ <b>Warning.</b>\n\n{text}")