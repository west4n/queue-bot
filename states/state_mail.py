import time

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State

from keyboards.kb_builder import inline_builder_text

from utils.sender import send_preview, start_sender

from main import bot

import database.requests as req


router = Router()


class CreateMessage(StatesGroup):
    theme_text = State()
    message_text = State()
    confirm_sender = State()


class BindMenuContent(StatesGroup):
    insurance_message = State()
    transfer_message = State()
    visas_message = State()


@router.message(CreateMessage.theme_text, F.text)
async def process_state_theme_text(message: Message, state: FSMContext):
    await state.update_data(theme_text=message.html_text)

    await message.answer(text="Тема принята, теперь отправьте текст рассылки:")

    await state.set_state(CreateMessage.message_text)


@router.message(CreateMessage.message_text, F.text)
async def process_state_message_text(message: Message, state: FSMContext):
    await state.update_data(message_text=message.html_text)
    data = await state.get_data()

    message_id = await send_preview(message, data)

    await state.update_data(message_id=message_id)

    await message.answer(
        text="<b>Сообщение сформировано!</b>\n\n" "Чтобы начать, нажмите кнопку ниже",
        reply_markup=inline_builder_text(
            text=["Отправить", "Отменить"], callback_data=["mail_start", "mail_cancel"]
        ),
    )

    await state.set_state(CreateMessage.confirm_sender)


@router.callback_query(CreateMessage.confirm_sender, F.data == "mail_start")
async def process_state_mail_start(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    await callback.message.edit_text(
        "Рассылка началась! 📨",
    )

    await state.clear()
    await callback.answer()

    user_ids = await req.get_users()
    t_start = time.time()
    message_id = data.get("message_id")
    count = await start_sender(
        bot,
        user_ids=user_ids,
        from_chat_id=callback.message.chat.id,
        message_id=message_id,
    )

    await callback.message.answer(
        f"Отправлено {count}/{len(user_ids)} за {round(time.time() - t_start)}c."
    )
