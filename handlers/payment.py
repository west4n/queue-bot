import logging

from aiogram import Router, F
from aiogram.types import Message, PreCheckoutQuery
from aiogram.fsm.context import FSMContext

from keyboards.kb_builder import inline_builder_text
from states.buy_call import BuyCallState
from services.analytics import log_event

import database.requests as req

logger = logging.getLogger(__name__)
router = Router()


@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """
    Обработка PreCheckoutQuery - запрос перед подтверждением платежа.
    Telegram требует ответ в течение 10 секунд, иначе возникает BOT_PRECHECKOUT_TIMEOUT.
    """
    try:
        # Проверяем, что это платеж в Telegram Stars
        if pre_checkout_query.currency != "XTR":
            await pre_checkout_query.bot.answer_pre_checkout_query(
                pre_checkout_query.id,
                ok=False,
                error_message="Поддерживаются только платежи через Telegram Stars."
            )
            return

        # Проверяем payload
        payload = pre_checkout_query.invoice_payload
        if not payload.startswith("call:"):
            await pre_checkout_query.bot.answer_pre_checkout_query(
                pre_checkout_query.id,
                ok=False,
                error_message="Неизвестный тип платежа."
            )
            return

        # Парсим payload для проверки
        parts = payload.split(":")
        if len(parts) < 4:
            await pre_checkout_query.bot.answer_pre_checkout_query(
                pre_checkout_query.id,
                ok=False,
                error_message="Ошибка в данных платежа."
            )
            return

        # Проверяем, что платеж от правильного пользователя
        user_id = int(parts[3])
        if user_id != pre_checkout_query.from_user.id:
            await pre_checkout_query.bot.answer_pre_checkout_query(
                pre_checkout_query.id,
                ok=False,
                error_message="Ошибка: платеж не соответствует пользователю."
            )
            return

        # Все проверки пройдены - подтверждаем платеж
        await pre_checkout_query.bot.answer_pre_checkout_query(
            pre_checkout_query.id,
            ok=True
        )
        logger.info(
            f"Pre-checkout query approved for user {pre_checkout_query.from_user.id}")

    except Exception as e:
        logger.error(f"Ошибка при обработке pre_checkout_query: {e}")
        # В случае ошибки все равно отвечаем, чтобы не было timeout
        try:
            await pre_checkout_query.bot.answer_pre_checkout_query(
                pre_checkout_query.id,
                ok=False,
                error_message="Произошла ошибка при обработке платежа. Попробуйте позже."
            )
        except Exception as answer_error:
            logger.error(
                f"Ошибка при ответе на pre_checkout_query: {answer_error}")


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext):
    """Обработка успешного платежа через Telegram Stars"""
    payment = message.successful_payment

    # Проверяем, что это платеж в Telegram Stars
    if payment.currency != "XTR":
        await message.answer(
            "Поддерживаются только платежи через Telegram Stars.",
            reply_markup=inline_builder_text(
                text="Вернуться в меню",
                callback_data="main_menu",
            ),
        )
        return

    # Парсим payload для определения типа покупки
    # Формат: call:{tracking_type}:{interval}:{user_id}
    payload = payment.invoice_payload

    if not payload.startswith("call:"):
        await message.answer(
            "Неизвестный тип платежа.",
            reply_markup=inline_builder_text(
                text="Вернуться в меню",
                callback_data="main_menu",
            ),
        )
        return

    parts = payload.split(":")
    if len(parts) < 4:
        await message.answer(
            "Ошибка в данных платежа.",
            reply_markup=inline_builder_text(
                text="Вернуться в меню",
                callback_data="main_menu",
            ),
        )
        return

    tracking_type = parts[1]
    interval = parts[2]
    user_id = int(parts[3])

    # Проверяем, что платеж от правильного пользователя
    if user_id != message.from_user.id:
        await message.answer(
            "Ошибка: платеж не соответствует пользователю.",
            reply_markup=inline_builder_text(
                text="Вернуться в меню",
                callback_data="main_menu",
            ),
        )
        return

    # Сохраняем платеж в БД
    try:
        await req.save_payment(
            tg_id=message.from_user.id,
            payment_charge_id=payment.telegram_payment_charge_id,
            amount=payment.total_amount
        )
        await log_event(message.from_user.id, "payment", {
            "payment_charge_id": payment.telegram_payment_charge_id,
            "amount": payment.total_amount,
            "payment_type": "call"
        })
    except Exception as e:
        # Логируем ошибку, но не прерываем процесс
        logger.error(f"Ошибка при сохранении платежа: {e}")

    # Сохраняем информацию о платеже в FSM для дальнейшего использования
    await state.update_data(
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
        tracking_type=tracking_type,
        tracking_interval=interval,
    )

    # Переходим к запросу номера телефона
    await message.answer(
        "<b>Платеж успешно обработан! ✅</b>\n\n"
        "Теперь поделитесь номером телефона для звонка.\n\n"
        "Вы можете:\n"
        "1. Нажать кнопку 'Поделиться номером телефона'\n"
        "2. Или ввести номер вручную в формате +375291234567",
    )

    # Запрашиваем контакт
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Поделиться номером телефона", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await message.answer(
        "Нажмите кнопку ниже, чтобы поделиться номером телефона:",
        reply_markup=contact_keyboard,
    )

    await state.set_state(BuyCallState.phone_number)
