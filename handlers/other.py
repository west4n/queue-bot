from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

router = Router()


@router.message(Command(commands="reset"))
async def process_message_reset(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "<b>Состояние бота успешно сброшено!</b>\n\n"
        "Теперь попробуйте нажать или написать команду /start"
    )
