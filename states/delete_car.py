from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup

from keyboards.kb_builder import inline_builder_text
from services.analytics import log_event

import database.requests as req


router = Router()


class DeleteCarState(StatesGroup):
    confirm = State()


@router.callback_query(F.data.startswith("delete_car:"), StateFilter(default_state))
async def process_callback_delete_car(callback: CallbackQuery, state: FSMContext):
    car_number = callback.data.split(":")[1]
    await state.update_data(car_number=car_number)

    await callback.message.edit_text(
        f"Вы уверены, что хотите удалить номер машины <b>{car_number}</b>?",
        reply_markup=inline_builder_text(
            text=["Да", "Нет"], callback_data=["delete_yes", "delete_no"], sizes=2
        ),
    )

    await state.set_state(DeleteCarState.confirm)


@router.callback_query(F.data == "delete_yes", StateFilter(DeleteCarState.confirm))
async def process_state_delete_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tg_id = callback.from_user.id
    car_number = data["car_number"]

    await req.delete_car_number(tg_id, car_number)
    await log_event(tg_id, "delete_car", {"car_number": car_number.upper()})

    await callback.message.edit_text(
        "Номер успешно удален!",
        reply_markup=inline_builder_text(
            text="Главное меню", callback_data="main_menu"
        ),
    )

    await state.clear()
