import asyncio
from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup

from keyboards.kb_builder import inline_builder_text

from lexicon.lexicon import (
    lexicon_buttons_borders_keys,
    lexicon_buttons_borders_values,
    lexicon_buttons_type_car_keys,
    lexicon_buttons_type_car_values,
    LEXICON_BUTTONS_BORDERS,
)
from services.border_api import fetch_monitoring_data, fetch_statistics_data
from services.analytics import log_event
from utils.queue_statistics import (
    parse_registration_date,
    calculate_waiting_time,
    format_waiting_time,
    count_priority_cars_last_24h,
    calculate_estimated_waiting_time,
)


router = Router()


class QueueCarState(StatesGroup):
    border = State()
    car_type = State()


@router.callback_query(F.data == "reg_car_first", StateFilter(default_state))
async def process_queue_car_callback(callback: CallbackQuery, state: FSMContext):
    await log_event(callback.from_user.id, "queue_stats_view_initiated")

    await callback.message.edit_text(
        "Выберите границу:",
        reply_markup=inline_builder_text(
            text=lexicon_buttons_borders_values,
            callback_data=lexicon_buttons_borders_keys,
            sizes=3,
        ),
    )

    await callback.answer()

    await state.set_state(QueueCarState.border)


@router.callback_query(
    StateFilter(QueueCarState.border), F.data.in_(lexicon_buttons_borders_keys)
)
async def process_state_border(callback: CallbackQuery, state: FSMContext):
    await state.update_data(border=callback.data)

    await callback.message.edit_text(
        "Выберите тип машины:",
        reply_markup=inline_builder_text(
            text=lexicon_buttons_type_car_values,
            callback_data=lexicon_buttons_type_car_keys,
        ),
    )

    await callback.answer()

    await state.set_state(QueueCarState.car_type)


@router.callback_query(
    StateFilter(QueueCarState.car_type), F.data.in_(
        lexicon_buttons_type_car_keys)
)
async def process_state_car_type(callback: CallbackQuery, state: FSMContext):
    await state.update_data(car_type=callback.data)
    data = await state.get_data()

    # Выполняем параллельные запросы для улучшения производительности
    response_data, response_statistic_data = await asyncio.gather(
        fetch_monitoring_data(data["border"]),
        fetch_statistics_data(data["border"])
    )

    # Обработка случая, когда запросы вернули None (ошибка)
    if response_data is None or response_statistic_data is None:
        await callback.message.edit_text(
            "Произошла ошибка при получении данных. Попробуйте позже.",
            reply_markup=inline_builder_text(
                text="Главное меню", callback_data="main_menu"
            ),
        )
        await callback.answer()
        await state.clear()
        return

    # Определяем ключи для типов транспорта
    if data["car_type"] == "car_type":
        car_type = "carLiveQueue"
        priority_type = "carPriority"
        car_type_last_hour = "carLastHour"
        car_type_last_day = "carLastDay"
        vehicle_name = "автомобилей"
        vehicle_name_single = "автомобиля"
    elif data["car_type"] == "truck_type":
        car_type = "truckLiveQueue"
        priority_type = "truckPriority"
        car_type_last_hour = "truckLastHour"
        car_type_last_day = "truckLastDay"
        vehicle_name = "грузовых авто"
        vehicle_name_single = "грузового авто"
    else:
        car_type = "busLiveQueue"
        priority_type = "busPriority"
        car_type_last_hour = "busLastHour"
        car_type_last_day = "busLastDay"
        vehicle_name = "автобусов"
        vehicle_name_single = "автобуса"

    border_name = LEXICON_BUTTONS_BORDERS[data["border"]]

    # Логируем просмотр статистики очереди
    await log_event(callback.from_user.id, "queue_stats_view", {
        "border": data["border"],
        "border_name": border_name,
        "car_type": data["car_type"]
    })

    # Получаем данные очереди
    queue_raw = response_data.get(car_type, [])
    priority_queue = response_data.get(priority_type, [])

    # Фильтруем только машины со статусом 2 (в очереди с order_id)
    # Как в research_brest_queue.py
    queue = [car for car in queue_raw if car.get("status") == 2]

    # Получаем статистику
    called_last_day = int(response_statistic_data.get(car_type_last_day, 0))
    called_last_hour = int(response_statistic_data.get(car_type_last_hour, 0))
    priority_last_24h = count_priority_cars_last_24h(priority_queue)

    # Рассчитываем темп вызова в час
    total_called_24h = called_last_day + priority_last_24h
    rate_per_hour = round(total_called_24h / 24,
                          2) if total_called_24h > 0 else 0.0

    # Получаем информацию о первом авто в очереди
    if len(queue) > 0:
        first_car = queue[0]
        registration_date_str = first_car.get("registration_date", "")
        order_id_raw = first_car.get("order_id")
        # Обрабатываем случай, когда order_id может быть None
        order_id = order_id_raw if order_id_raw is not None else 0

        # Рассчитываем время ожидания первого авто
        reg_date = parse_registration_date(registration_date_str)
        if reg_date:
            waiting_time = calculate_waiting_time(reg_date)
            waiting_time_str = format_waiting_time(
                waiting_time["days"],
                waiting_time["hours"],
                waiting_time["minutes"]
            )
        else:
            waiting_time_str = "Не определено"

        # Рассчитываем примерное ожидание при регистрации сейчас
        # Используем общее количество машин в очереди + 1, как в research_brest_queue.py
        # Если сейчас в очереди N машин, то новый автомобиль будет (N+1)-м
        if rate_per_hour > 0:
            total_cars = len(queue)
            new_car_position = total_cars + 1
            estimated_waiting = calculate_estimated_waiting_time(
                new_car_position, rate_per_hour)
            estimated_waiting_str = format_waiting_time(
                estimated_waiting["days"],
                estimated_waiting["hours"],
                estimated_waiting["minutes"]
            )
            current_time_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        else:
            estimated_waiting_str = "Не определено"
            current_time_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    else:
        registration_date_str = "Нет машин в очереди"
        order_id = 0
        waiting_time_str = "Нет данных"
        estimated_waiting_str = "Нет данных"
        current_time_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Формируем дружелюбное сообщение со статистикой
    if data["car_type"] == "car_type":
        vehicle_emoji = "🚗"
        vehicle_name_plural = "автомобилей"
        vehicle_name_single = "автомобиля"
    elif data["car_type"] == "truck_type":
        vehicle_emoji = "🚛"
        vehicle_name_plural = "грузовых авто"
        vehicle_name_single = "грузового авто"
    else:
        vehicle_emoji = "🚌"
        vehicle_name_plural = "автобусов"
        vehicle_name_single = "автобуса"

    # Начало сообщения с приветствием
    message = f'📊 <b>Статистика очереди на границе "{border_name}"</b>\n\n'
    message += f'{vehicle_emoji} <b>Автомобилей в очереди:</b> {len(queue)}\n\n'

    # Статистика за 24 часа
    message += f'📅 <b>Вызвано машин за 24ч:</b> {called_last_day}'
    if priority_last_24h > 0:
        message += f' + {priority_last_24h} по приоритету ⚡'
    message += '\n'

    # Статистика за последний час
    message += f'⏰ <b>Вызвано машин за последний час:</b> {called_last_hour}\n\n'

    # Темп вызова
    message += f'⚡ <b>Темп вызова машин в час:</b> {rate_per_hour}\n'

    # Добавляем комментарий о темпе
    if rate_per_hour > 0:
        if rate_per_hour < 20:
            message += ' (низкий темп 😞)'
        elif rate_per_hour < 35:
            message += ' (нормальный темп 👍)'
        else:
            message += ' (высокий темп 🚀)'
    message += '\n\n'

    # Время ожидания первого авто
    if len(queue) > 0 and order_id > 0:
        message += (
            f'⏳ <b>Время ожидания первого {vehicle_name_single} в очереди:</b> '
            f'{waiting_time_str}\n'
        )

    # Примерное ожидание при регистрации сейчас
    if len(queue) > 0 and rate_per_hour > 0:
        message += (
            f'🔮 <b>Примерный подсчет ожидания при регистрации в ЗО сейчас:</b>'
            f' {estimated_waiting_str} ({current_time_str})'
        )
    elif len(queue) == 0:
        message += '✅ Очередь пуста! Можно ехать без ожидания 🎉'
    elif rate_per_hour == 0:
        message += '⚠️ Невозможно рассчитать ожидание (темп вызова = 0)'

    await callback.message.edit_text(
        message,
        reply_markup=inline_builder_text(
            text=["Назад", "В меню"], callback_data=["reg_car_first", "main_menu"], sizes=[1, 1]
        ),
    )

    await state.clear()
