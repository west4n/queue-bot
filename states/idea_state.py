import logging
from html import escape

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from config_data.config import ADMIN_IDS
from keyboards.kb_builder import inline_builder_text
from lexicon.lexicon import LEXICON_TEXT_IDEA
from services.analytics import log_event


logger = logging.getLogger(__name__)
router = Router()


class IdeaState(StatesGroup):
    waiting_message = State()


@router.message(IdeaState.waiting_message)
async def process_idea_message(message: Message, state: FSMContext):
    user = message.from_user
    username = f"@{user.username}" if user.username else "не указан"
    full_name = escape(user.full_name or "не указано")

    admin_context_text = (
        "<b>Новая идея от пользователя</b>\n\n"
        f"ID: <code>{user.id}</code>\n"
        f"Username: {escape(username)}\n"
        f"Имя: {full_name}"
    )

    delivered_count = 0
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            await message.bot.send_message(chat_id=admin_id, text=admin_context_text)
            delivered_count += 1
        except Exception as error:
            logger.error(
                "Не удалось отправить идею администратору %s от пользователя %s: %s",
                admin_id,
                user.id,
                error,
            )

    await log_event(
        user.id,
        "idea_submitted",
        {
            "delivered_admins": delivered_count,
            "total_admins": len(ADMIN_IDS),
            "message_type": message.content_type,
        },
    )

    if delivered_count == 0:
        await message.answer(
            LEXICON_TEXT_IDEA["delivery_error"],
            reply_markup=inline_builder_text(
                text="В меню",
                callback_data="main_menu",
            ),
        )
    else:
        await message.answer(
            LEXICON_TEXT_IDEA["thank_you"],
            reply_markup=inline_builder_text(
                text="В меню",
                callback_data="main_menu",
            ),
        )

    await state.clear()
