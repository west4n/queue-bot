from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup

from keyboards.kb_builder import inline_builder_text
from services.analytics import log_event

import database.requests as req


router = Router()


class AddCarState(StatesGroup):
    car_number = State()


@router.callback_query(F.data == "add_car", StateFilter(default_state))
async def process_callback_add_car(callback: CallbackQuery, state: FSMContext):
    await log_event(callback.from_user.id, "add_car_initiated")

    await callback.message.edit_text(
        "Введите номер машины латиницей в формате <b>1234AX7</b>",
        reply_markup=inline_builder_text(
            text="Вернуться в меню",
            callback_data="main_menu",
        ),
    )

    await state.set_state(AddCarState.car_number)


@router.message(
    F.text.regexp(r"^[a-zA-Z0-9]{6,10}$"), StateFilter(AddCarState.car_number)
)
async def process_state_car_number(message: Message, state: FSMContext):
    await state.update_data(car_number=message.text)
    data = await state.get_data()

    tg_id = message.from_user.id
    car_number = data["car_number"]
    await req.set_car_number(tg_id, car_number)

    await log_event(tg_id, "add_car", {"car_number": car_number.upper()})

    await message.answer(
        "Машина добавлена",
        reply_markup=inline_builder_text(
            text=["Просмотреть мои машины", "Вернуться в меню"],
            callback_data=["my_cars", "main_menu"],
        ),
    )

    await state.clear()
