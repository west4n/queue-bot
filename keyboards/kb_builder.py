from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


def inline_builder_text(
    text: str | list[str],
    callback_data: str | list[str],
    sizes: int | list[int] = 1,
    **kwargs,
) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()

    if isinstance(text, str):
        text = [text]
    if isinstance(callback_data, str):
        callback_data = [callback_data]
    if isinstance(sizes, int):
        sizes = [sizes]

    [builder.button(text=txt, callback_data=cb) for txt, cb in zip(text, callback_data)]

    builder.adjust(*sizes)

    return builder.as_markup(**kwargs)


def inline_build_car_buttons(car_numbers):
    builder = InlineKeyboardBuilder()

    for car_number in car_numbers:
        builder.row(
            InlineKeyboardButton(text=car_number, callback_data=f"car:{car_number}"),
            InlineKeyboardButton(
                text="Удалить", callback_data=f"delete_car:{car_number}"
            ),
        )

    builder.row(InlineKeyboardButton(text="Добавить машину", callback_data="add_car"))
    builder.row(
        InlineKeyboardButton(text="Вернуться в меню", callback_data="main_menu")
    )

    return builder.as_markup()


def inline_build_car_buttons_without_add(car_numbers):
    builder = InlineKeyboardBuilder()

    for car_number in car_numbers:
        builder.row(
            InlineKeyboardButton(text=car_number, callback_data=f"car:{car_number}"),
            InlineKeyboardButton(
                text="Удалить", callback_data=f"delete_car:{car_number}"
            ),
        )

    builder.row(
        InlineKeyboardButton(text="Вернуться в меню", callback_data="main_menu")
    )

    return builder.as_markup()


def inline_build_group(name: str, url: str):
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text=name, url=url))

    return builder.as_markup()


def inline_build_group_with_menu(name: str, url: str):
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text=name, url=url))
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="main_menu"))

    return builder.as_markup()


def inline_build_group_with_alert(name: str, url: str):
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text=name, url=url))
    builder.row(
        InlineKeyboardButton(text="Отменить уведомления", callback_data="remove_alert")
    )
    builder.row(InlineKeyboardButton(text="В меню", callback_data="main_menu"))

    return builder.as_markup()
