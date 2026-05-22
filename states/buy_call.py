import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import LabeledPrice

from keyboards.kb_builder import inline_builder_text
from services.analytics import log_event

from config_data.config import Config, load_config
import database.requests as req

logger = logging.getLogger(__name__)
router = Router()
config: Config = load_config()


class BuyCallState(StatesGroup):
    phone_number = State()
    queue_number = State()


@router.callback_query(F.data.startswith("buy_call:"))
async def process_callback_buy_call(callback: CallbackQuery, state: FSMContext):
    """Инициирование покупки звонка - отправка invoice через Telegram Stars или переход к запросу телефона в тестовом режиме"""
    # Формат callback_data: buy_call:{tracking_type}:{interval}
    # Например: buy_call:minutes:5 или buy_call:queue:15

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Ошибка в данных", show_alert=True)
        return

    tracking_type = parts[1]  # minutes или queue
    interval = parts[2]  # 5, 10, 15 или 15, 30

    await log_event(callback.from_user.id, "buy_call_initiated", {
        "tracking_type": tracking_type,
        "interval": interval
    })

    # Сохраняем информацию о типе отслеживания для дальнейшего использования
    await state.update_data(
        tracking_type=tracking_type,
        tracking_interval=interval
    )

    # Проверяем режим работы
    if config.call_mode == "test":
        # В тестовом режиме пропускаем оплату и сразу переходим к запросу телефона
        await state.update_data(
            telegram_payment_charge_id="TEST_MODE"
        )

        await callback.message.edit_text(
            "<b>Тестовый режим активирован 🧪</b>\n\n"
            "Оплата не требуется. Поделитесь номером телефона для звонка.\n\n"
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

        await callback.message.answer(
            "Нажмите кнопку ниже, чтобы поделиться номером телефона:",
            reply_markup=contact_keyboard,
        )

        await state.set_state(BuyCallState.phone_number)
        await callback.answer()
    else:
        # В продакшн режиме отправляем invoice
        payload = f"call:{tracking_type}:{interval}:{callback.from_user.id}"

        # Отправляем invoice с Telegram Stars
        await callback.message.answer_invoice(
            title="Телефонный звонок при приближении очереди",
            description=f"Вы получите телефонный звонок, когда ваша очередь достигнет указанного номера",
            payload=payload,
            provider_token="",  # Пустая строка для Telegram Stars
            currency="XTR",  # XTR для Telegram Stars
            prices=[LabeledPrice(label="Телефонный звонок",
                                 amount=config.call_star_price)],
            need_phone_number=False,  # Будем запрашивать отдельно после оплаты
        )

        await callback.answer()


@router.message(F.contact, StateFilter(BuyCallState.phone_number))
async def process_state_phone_number_contact(message: Message, state: FSMContext):
    """Обработка номера телефона из контакта"""
    phone_number = message.contact.phone_number
    # Убеждаемся, что номер начинается с +
    if not phone_number.startswith("+"):
        phone_number = f"+{phone_number}"

    await state.update_data(phone_number=phone_number)

    # Получаем информацию о типе отслеживания для предупреждения
    data = await state.get_data()
    tracking_type = data.get("tracking_type")
    tracking_interval = data.get("tracking_interval")

    # Формируем предупреждение в зависимости от типа отслеживания
    if tracking_type == "minutes":
        warning_text = (
            f"⚠️ <b>Важно:</b> Мониторинг работает каждые <b>{tracking_interval} минут</b>.\n\n"
            f"За это время ваша очередь может стать ближе указанного номера, "
            f"но звонок поступит в любом случае, когда очередь достигнет или станет меньше указанного значения.\n\n"
            f"Также звонок поступит, если вас вызовут на пропускной пункт раньше."
        )
    elif tracking_type == "queue":
        warning_text = (
            f"⚠️ <b>Важно:</b> Мониторинг работает каждые <b>{tracking_interval} минут</b>.\n\n"
            f"За это время ваша очередь может стать ближе указанного номера, "
            f"но звонок поступит в любом случае, когда очередь достигнет или станет меньше указанного значения.\n\n"
            f"Также звонок поступит, если вас вызовут на пропускной пункт раньше."
        )
    else:
        warning_text = (
            f"⚠️ <b>Важно:</b> Мониторинг работает по времени.\n\n"
            f"За время между проверками ваша очередь может стать ближе указанного номера, "
            f"но звонок поступит в любом случае, когда очередь достигнет или станет меньше указанного значения.\n\n"
            f"Также звонок поступит, если вас вызовут на пропускной пункт раньше."
        )

    # Удаляем клавиатуру после получения контакта
    from aiogram.types import ReplyKeyboardRemove

    await message.answer(
        f"Номер телефона получен: <b>{phone_number}</b>\n\n"
        f"{warning_text}\n\n"
        f"Теперь введите номер очереди, при котором должен поступить звонок (например, 25):",
        reply_markup=ReplyKeyboardRemove(),
    )

    await state.set_state(BuyCallState.queue_number)


@router.message(
    F.text.regexp(
        r"^\+?[1-9]\d{1,14}$"), StateFilter(BuyCallState.phone_number)
)
async def process_state_phone_number_text(message: Message, state: FSMContext):
    """Обработка номера телефона в текстовом формате"""
    phone_number = message.text.strip()
    # Убеждаемся, что номер начинается с +
    if not phone_number.startswith("+"):
        phone_number = f"+{phone_number}"

    await state.update_data(phone_number=phone_number)

    # Получаем информацию о типе отслеживания для предупреждения
    data = await state.get_data()
    tracking_type = data.get("tracking_type")
    tracking_interval = data.get("tracking_interval")

    # Формируем предупреждение в зависимости от типа отслеживания
    if tracking_type == "minutes":
        warning_text = (
            f"⚠️ <b>Важно:</b> Мониторинг работает каждые <b>{tracking_interval} минут</b>.\n\n"
            f"За это время ваша очередь может стать ближе указанного номера, "
            f"но звонок поступит в любом случае, когда очередь достигнет или станет меньше указанного значения.\n\n"
            f"Также звонок поступит, если вас вызовут на пропускной пункт раньше."
        )
    elif tracking_type == "queue":
        warning_text = (
            f"⚠️ <b>Важно:</b> Мониторинг работает каждые <b>{tracking_interval} минут</b>.\n\n"
            f"За это время ваша очередь может стать ближе указанного номера, "
            f"но звонок поступит в любом случае, когда очередь достигнет или станет меньше указанного значения.\n\n"
            f"Также звонок поступит, если вас вызовут на пропускной пункт раньше."
        )
    else:
        warning_text = (
            f"⚠️ <b>Важно:</b> Мониторинг работает по времени.\n\n"
            f"За время между проверками ваша очередь может стать ближе указанного номера, "
            f"но звонок поступит в любом случае, когда очередь достигнет или станет меньше указанного значения.\n\n"
            f"Также звонок поступит, если вас вызовут на пропускной пункт раньше."
        )

    # Удаляем клавиатуру если она была показана
    from aiogram.types import ReplyKeyboardRemove

    await message.answer(
        f"Номер телефона получен: <b>{phone_number}</b>\n\n"
        f"{warning_text}\n\n"
        f"Теперь введите номер очереди, при котором должен поступить звонок (например, 25):",
        reply_markup=ReplyKeyboardRemove(),
    )

    await state.set_state(BuyCallState.queue_number)


@router.message(
    F.text.regexp(r"^\d+$"), StateFilter(BuyCallState.queue_number)
)
async def process_state_queue_number(message: Message, state: FSMContext):
    """Обработка номера очереди"""
    queue_number = int(message.text.strip())

    if queue_number <= 0:
        await message.answer(
            "Номер очереди должен быть положительным числом. Попробуйте еще раз:",
        )
        return

    data = await state.get_data()
    phone_number = data.get("phone_number")
    payment_charge_id = data.get("telegram_payment_charge_id")

    # Получаем данные о типе отслеживания из состояния
    tracking_type = data.get("tracking_type")
    tracking_interval = data.get("tracking_interval")

    if not phone_number:
        await message.answer(
            "Ошибка: не найден номер телефона. Пожалуйста, начните процесс заново.",
            reply_markup=inline_builder_text(
                text="Вернуться в меню",
                callback_data="main_menu",
            ),
        )
        await state.clear()
        return

    # В тестовом режиме используем фиктивный payment_charge_id, если его нет
    # В prod режиме payment_charge_id уже должен быть сохранен в process_successful_payment
    if not payment_charge_id:
        # Это тестовый режим - создаем фиктивный payment_charge_id
        payment_charge_id = f"TEST_MODE_{message.from_user.id}_{int(datetime.now().timestamp())}"
        try:
            await req.save_payment(
                tg_id=message.from_user.id,
                payment_charge_id=payment_charge_id,
                amount=config.call_star_price
            )
        except Exception as e:
            logger.error(f"Ошибка при сохранении тестового платежа: {e}")

    # Сохраняем информацию о звонке в БД
    await req.set_call_info(
        tg_id=message.from_user.id,
        phone_number=phone_number,
        queue_number=queue_number,
        payment_charge_id=payment_charge_id,
    )

    # Логируем событие покупки звонка
    await log_event(message.from_user.id, "buy_call", {
        "tracking_type": tracking_type or "unknown",
        "tracking_interval": tracking_interval or "unknown",
        "queue_number": queue_number,
        "is_test_mode": payment_charge_id.startswith("TEST_MODE") if payment_charge_id else False
    })

    # Сохраняем информацию о том, что нужно запустить отслеживание
    # Отслеживание будет запущено через callback start_tracking после завершения процесса покупки
    # Пользователю нужно будет нажать кнопку для запуска отслеживания

    # Формируем callback_data для запуска отслеживания
    # Если tracking_type или tracking_interval отсутствуют, используем значения по умолчанию
    if tracking_type and tracking_interval:
        start_tracking_callback = f"start_tracking:{tracking_type}:{tracking_interval}"
    else:
        # Если данные отсутствуют, не показываем кнопку запуска отслеживания
        start_tracking_callback = None

    # Формируем сообщение и клавиатуру
    message_text = (
        f"<b>Отлично! Настройки сохранены.</b>\n\n"
        f"Номер телефона: <b>{phone_number}</b>\n"
        f"Звонок поступит, когда ваша очередь достигнет: <b>{queue_number}</b>\n\n"
    )

    if start_tracking_callback:
        message_text += "Теперь запустите отслеживание:"
        reply_markup = inline_builder_text(
            text=["Запустить отслеживание", "Вернуться в меню"],
            callback_data=[start_tracking_callback, "main_menu"],
            sizes=[1, 1],
        )
    else:
        message_text += "Для запуска отслеживания используйте главное меню."
        reply_markup = inline_builder_text(
            text="Вернуться в меню",
            callback_data="main_menu",
        )

    await message.answer(
        message_text,
        reply_markup=reply_markup,
    )

    await state.clear()
