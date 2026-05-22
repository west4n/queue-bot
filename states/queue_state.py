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
from services.border_api import fetch_monitoring_data
from services.analytics import log_event


router = Router()


class QueueState(StatesGroup):
    border = State()
    car_type = State()


@router.callback_query(F.data == "queue", StateFilter(default_state))
async def process_queue_callback(callback: CallbackQuery, state: FSMContext):
    await log_event(callback.from_user.id, "queue_view_initiated")

    await callback.message.edit_text(
        "Выберите границу:",
        reply_markup=inline_builder_text(
            text=lexicon_buttons_borders_values,
            callback_data=lexicon_buttons_borders_keys,
            sizes=3,
        ),
    )

    await callback.answer()

    await state.set_state(QueueState.border)


@router.callback_query(
    StateFilter(QueueState.border), F.data.in_(lexicon_buttons_borders_keys)
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

    await state.set_state(QueueState.car_type)


@router.callback_query(
    StateFilter(QueueState.car_type), F.data.in_(lexicon_buttons_type_car_keys)
)
async def process_state_car_type(callback: CallbackQuery, state: FSMContext):
    await state.update_data(car_type=callback.data)
    data = await state.get_data()

    print("car_type")

    border_name = LEXICON_BUTTONS_BORDERS[data["border"]]

    response_data = await fetch_monitoring_data(data["border"])

    # Обработка случая, когда запрос вернул None (ошибка)
    if response_data is None:
        await callback.message.edit_text(
            "Произошла ошибка при получении данных. Попробуйте позже.",
            reply_markup=inline_builder_text(
                text="Главное меню", callback_data="main_menu"
            ),
        )
        await callback.answer()
        await state.clear()
        return

    if data["car_type"] == "car_type":
        car_type = "carLiveQueue"
    elif data["car_type"] == "truck_type":
        car_type = "truckLiveQueue"
    else:
        car_type = "busLiveQueue"

    queue = response_data[car_type]
    queue_length = len(queue)

    # Логируем просмотр очереди
    await log_event(callback.from_user.id, "queue_view", {
        "border": data["border"],
        "border_name": border_name,
        "car_type": data["car_type"],
        "queue_length": queue_length
    })

    if data["car_type"] == "car_type":
        message = f"ЗО: <b>{border_name}</b>\nКоличество легковых машин: <b>{queue_length}</b>"
    elif data["car_type"] == "truck_type":
        message = f"ЗО: <b>{border_name}</b>\nКоличество грузовых машин: <b>{queue_length}</b>"
    else:
        message = (
            f"ЗО: <b>{border_name}</b>\nКоличество автобусов: <b>{queue_length}</b>"
        )

    await callback.message.edit_text(
        message,
        reply_markup=inline_builder_text(
            text="Главное меню", callback_data="main_menu"
        ),
    )

    await callback.answer()

    await state.clear()
