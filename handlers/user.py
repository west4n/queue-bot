import database.requests as req

from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import default_state
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from config_data.config import load_config
from lexicon.lexicon import (
    LEXICON_TEXT_START,
    LEXICON_TEXT_SUPPORT,
    LEXICON_TEXT_IDEA,
)
from states.idea_state import IdeaState

from keyboards.kb_builder import inline_builder_text, inline_build_group_with_menu
from services.analytics import log_event


router = Router()
config = load_config()
MENU_SEPARATOR_TEXT = "\u200b"


def build_main_menu(car_numbers: int):
    return inline_builder_text(
        text=[
            "Камеры",
            "Страховки",
            "Инд. трансфер",
            f"Мои машины ({car_numbers} из 3)",
            "Статистика очереди",
            MENU_SEPARATOR_TEXT,
            "Поддержка",
            "Есть идея",
        ],
        callback_data=[
            "show_camera",
            "insurances",
            "individual_transfer",
            "my_cars",
            "reg_car_first",
            "menu_separator",
            "support_stub",
            "idea_stub",
        ],
        sizes=[2, 2, 1, 1, 2],
    )


@router.message(CommandStart(), StateFilter(default_state))
@router.callback_query(F.data.in_({"main_menu", "delete_no"}))
async def process_start_command(message: Message | CallbackQuery, state: FSMContext):
    tg_id = message.from_user.id
    is_new_user = await req.set_user(tg_id, message.from_user.first_name)

    # Логируем событие
    if isinstance(message, Message) and message.text and message.text.startswith('/start'):
        # Это команда /start - регистрация или возврат
        await log_event(tg_id, "start", {"is_new_user": is_new_user})
    else:
        # Это возврат в главное меню
        await log_event(tg_id, "main_menu")

    user = await req.get_user(tg_id)

    if user.car_numbers is None:
        car_numbers = 0
    else:
        car_numbers = len(user.car_numbers)
    main_menu_markup = build_main_menu(car_numbers)

    if isinstance(message, CallbackQuery):
        await message.message.edit_text(
            f'{LEXICON_TEXT_START["greeting"]}',
            reply_markup=main_menu_markup,
        )

        await state.clear()
    else:
        await message.answer(
            f'{LEXICON_TEXT_START["greeting"]}',
            reply_markup=main_menu_markup,
        )


@router.callback_query(F.data == "support_stub", StateFilter(default_state))
async def process_support_button(callback: CallbackQuery):
    await callback.answer()

    if not config.support_url:
        await callback.message.edit_text(
            LEXICON_TEXT_SUPPORT["unavailable"],
            reply_markup=inline_builder_text(
                text="В меню",
                callback_data="main_menu",
            ),
        )
        return

    await callback.message.edit_text(
        LEXICON_TEXT_SUPPORT["contact_card"],
        reply_markup=inline_build_group_with_menu(
            name="Написать в поддержку",
            url=config.support_url,
        ),
    )


@router.callback_query(F.data == "idea_stub", StateFilter(default_state))
async def process_idea_button(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await log_event(callback.from_user.id, "idea_initiated")
    await callback.message.edit_text(
        LEXICON_TEXT_IDEA["instruction"],
        reply_markup=inline_builder_text(
            text="В меню",
            callback_data="main_menu",
        ),
    )
    await state.set_state(IdeaState.waiting_message)


async def send_bound_content(callback: CallbackQuery, content_key: str):
    await callback.answer()
    content = await req.get_menu_content(content_key)

    if not content:
        await callback.message.edit_text(
            "Раздел временно недоступен.\n\nКонтент еще не настроен администратором.",
            reply_markup=inline_builder_text(
                text="В меню",
                callback_data="main_menu",
            ),
        )
        return

    try:
        await callback.bot.copy_message(
            chat_id=callback.from_user.id,
            from_chat_id=content.source_chat_id,
            message_id=content.source_message_id,
        )
    except TelegramBadRequest as error:
        error_text = str(error).lower()
        if "protected" in error_text or "can't be copied" in error_text:
            fallback_text = (
                "Сохраненное сообщение защищено от копирования.\n\n"
                "Попросите администратора привязать другой вариант контента."
            )
        else:
            fallback_text = (
                "Не удалось отправить сохраненное сообщение.\n\n"
                "Попросите администратора заново привязать контент."
            )
        await callback.message.edit_text(
            fallback_text,
            reply_markup=inline_builder_text(
                text="В меню",
                callback_data="main_menu",
            ),
        )


@router.callback_query(F.data.in_({"insurances", "insurances_stub"}), StateFilter(default_state))
async def process_insurance_button(callback: CallbackQuery):
    await send_bound_content(callback, "insurance")


@router.callback_query(
    F.data.in_({"individual_transfer", "individual_transfer_stub"}),
    StateFilter(default_state),
)
async def process_transfer_button(callback: CallbackQuery):
    await send_bound_content(callback, "individual_transfer")


@router.callback_query(F.data == "menu_separator", StateFilter(default_state))
async def process_menu_separator(callback: CallbackQuery):
    await callback.answer()
