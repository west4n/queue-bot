from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.state import default_state

from keyboards.kb_builder import (
    inline_builder_text,
    inline_build_car_buttons,
    inline_build_car_buttons_without_add,
)

from lexicon.lexicon import (
    lexicon_buttons_add_car_keys,
    lexiocn_buttons_add_car_values,
    lexicon_buttons_minutes_keys,
    lexicon_buttons_minutes_values,
    lexicon_buttons_cars_keys,
    lexicon_buttons_cars_values,
)

from services.find_my_car import find_my_car
from services.analytics import log_event

import database.requests as req

router = Router()

tracking_tasks = {}


@router.callback_query(F.data == "my_cars", StateFilter(default_state))
async def process_callback_my_cars(callback: CallbackQuery):
    tg_id = callback.from_user.id
    await log_event(tg_id, "my_cars_view")

    user = await req.get_user(tg_id)

    if user and user.car_numbers is None or not user.car_numbers:
        await callback.message.edit_text(
            "<b>Машин не найдено!</b>\n\n" "Хотите добавить машину?",
            reply_markup=inline_builder_text(
                text=lexiocn_buttons_add_car_values,
                callback_data=lexicon_buttons_add_car_keys,
            ),
        )
    else:
        if len(user.car_numbers) < 3:
            keyboard: InlineKeyboardMarkup = inline_build_car_buttons(
                user.car_numbers)
            await callback.message.edit_text(
                "<b>Ваши машины</b> 🚗 \n\n"
                "Что можно делать:\n"
                "1. Вы можете добавлять до <b>трёх</b> номеров\n"
                "2. Нажмите на номер машины, чтобы попасть в меню для отслеживания очереди",
                reply_markup=keyboard,
            )
        else:
            keyboard: InlineKeyboardMarkup = inline_build_car_buttons_without_add(
                user.car_numbers
            )
            await callback.message.edit_text(
                "<b>Ваши машины</b> 🚗 \n\n"
                "Что можно делать:\n"
                "1. Вы можете добавлять до <b>трёх</b> номеров\n"
                "2. Нажмите на номер машины, чтобы попасть в меню для отслеживания очереди",
                reply_markup=keyboard,
            )


@router.callback_query(F.data.startswith("car:"), StateFilter(default_state))
async def process_callback_track_car(callback: CallbackQuery):
    tg_id = callback.from_user.id
    car_number = callback.data.split(":")[1]

    await log_event(tg_id, "car_selected", {"car_number": car_number.upper()})

    car_info = await find_my_car(car_number)

    if car_info is None:
        await callback.message.edit_text(
            "Машина не найдена!",
            reply_markup=inline_builder_text(
                text="Главное меню", callback_data="main_menu"
            ),
        )
    else:
        car_status = car_info["car"].get("status")
        order_id = car_info["car"].get("order_id")

        # Формируем сообщение в зависимости от статуса
        if car_status == 2:
            # Машина в очереди
            order_id_text = str(
                order_id) if order_id is not None else "Не указан"
            status_text = f'Номер в очереди: <b>{order_id_text}</b>'
        elif car_status == 3:
            # Машина вызвана в ПП
            status_text = '<b>Машина вызвана на пропускной пункт</b>'
        elif car_status == 9:
            # Другой статус (возможно, обработана)
            status_text = '<b>Машина обработана</b>'
        else:
            # Неизвестный статус
            order_id_text = str(
                order_id) if order_id is not None else "Не указан"
            status_text = f'Номер в очереди: <b>{order_id_text}</b> (статус: {car_status})'

        await callback.message.edit_text(
            f"Машина найдена!\n\n"
            f'ЗО: <b>{car_info["border"]["border_name"]}</b>\n'
            f'{status_text}\n'
            f'Время и дата регистрации: <b>{car_info["car"]["registration_date"]}</b>\n\n'
            f"Теперь вы можете выбрать:\n\n"
            f"1. Следить за машиной каждые 5, 10, 15 минут\n"
            f"2. Следить каждые 15, 30 машин",
            reply_markup=inline_builder_text(
                text=lexicon_buttons_minutes_values
                + lexicon_buttons_cars_values
                + ["Вернуться в меню"],
                callback_data=lexicon_buttons_minutes_keys
                + lexicon_buttons_cars_keys
                + ["main_menu"],
                sizes=[3, 2, 1],
            ),
        )

        await req.set_active_car_number(callback.from_user.id, car_number)
