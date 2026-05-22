import asyncio

from aiogram import Bot

from keyboards.kb_builder import (
    inline_build_group,
    inline_build_group_with_menu,
    inline_builder_text,
)

from services.find_my_car import find_my_car
from services.twilio_service import make_call
import database.requests as req


async def track_car_minutes(bot: Bot, tg_id, car_number: str, interval: int):
    await bot.send_message(
        tg_id,
        f"<b>Уведомления успешно включены! 🔔</b>\n\n"
        f"Уведомления будут приходить каждые <b>{interval}</b> минут\n\n"
        f"Пока вы ожидаете, вы можете перейти в нашу группу",
        reply_markup=inline_build_group(
            name="Попутчики 🙋 Водители 🚘", url="tg://resolve?domain=travelersminsk"
        ),
    )

    call_made = False  # Флаг для отслеживания, был ли совершен звонок

    while True:
        # Загружаем информацию о звонке на каждой итерации для актуальности данных
        call_info = await req.get_call_info(tg_id)
        car_info = await find_my_car(car_number)

        if car_info is not None and car_info["car"]["status"] == 2:
            # Машина все еще в очереди, отправляем обновленный order_id
            order_id = car_info["car"].get("order_id")
            order_id_text = str(
                order_id) if order_id is not None else "Не указан"

            # Проверяем условия для звонка
            if (call_info and
                call_info.get("call_purchased") and
                not call_info.get("call_completed") and
                order_id is not None and
                    call_info.get("call_queue_number") is not None):

                # Проверяем, достиг ли номер очереди целевого значения (с учетом перепрыгивания)
                if order_id <= call_info["call_queue_number"]:
                    # Совершаем звонок только один раз
                    if not call_made:
                        phone_number = call_info.get("phone_number")
                        if phone_number:
                            message = (
                                f"Ваша очередь приближается! "
                                f"Текущий номер в очереди: {order_id}. "
                                f"Приготовьтесь к пропускному пункту."
                            )
                            call_sid = await make_call(phone_number, message, prevent_answer=True)

                            if call_sid:
                                await req.mark_call_completed(tg_id)
                                call_info["call_completed"] = True
                                await bot.send_message(
                                    tg_id,
                                    f"<b>📞 Вам совершен телефонный звонок!</b>\n\n"
                                    f"Ваш номер в очереди: <b>{order_id}</b>\n"
                                    f"Приготовьтесь к пропускному пункту.",
                                    reply_markup=inline_builder_text(
                                        text=["Отменить уведомления", "В меню"],
                                        callback_data=["remove_alert", "main_menu"],
                                        sizes=[1, 1],
                                    ),
                                )
                                call_made = True

            await bot.send_message(
                tg_id,
                f'ЗО: <b>{car_info["border"]["border_name"]}</b>\n'
                f'Номер в очереди: <b>{order_id_text}</b>\n'
                f"Интервал: <b>{interval} минут</b>",
                reply_markup=inline_builder_text(
                    text=["Отменить уведомления", "В меню"],
                    callback_data=["remove_alert", "main_menu"],
                    sizes=[1, 1],
                ),
            )
        elif car_info is not None and car_info["car"]["status"] in [1, 3]:
            # Машину вызвали (статус 1 или 3 означает вызвана в ПП)

            # Проверяем, был ли куплен звонок, но еще не совершен
            if (call_info and
                call_info.get("call_purchased") and
                not call_info.get("call_completed") and
                    not call_made):
                # Отправляем звонок сразу, так как машина вызвана
                phone_number = call_info.get("phone_number")
                if phone_number:
                    order_id = car_info["car"].get("order_id")
                    order_id_text = str(
                        order_id) if order_id is not None else "вызвана"
                    message = (
                        f"Ваша машина вызвана на пропускной пункт! "
                        f"Номер в очереди: {order_id_text}. "
                        f"Приготовьтесь к пропускному пункту."
                    )
                    call_sid = await make_call(phone_number, message, prevent_answer=True)

                    if call_sid:
                        await req.mark_call_completed(tg_id)
                        await bot.send_message(
                            tg_id,
                            f"<b>📞 Вам совершен телефонный звонок!</b>\n\n"
                            f"Ваша машина вызвана на пропускной пункт.\n"
                            f"Номер в очереди: <b>{order_id_text}</b>\n\n"
                            f"<b>Счастливого пути!👋</b>",
                            reply_markup=inline_builder_text(
                                text="Вернуться в меню", callback_data="main_menu"
                            ),
                        )
                    else:
                        await bot.send_message(
                            tg_id,
                            "Ваша машина вызвана на пропускной пункт.\n\n"
                            "<b>Счастливого пути!👋</b>",
                            reply_markup=inline_builder_text(
                                text="Вернуться в меню", callback_data="main_menu"
                            ),
                        )
                else:
                    await bot.send_message(
                        tg_id,
                        "Ваша машина вызвана на пропускной пункт.\n\n"
                        "<b>Счастливого пути!👋</b>",
                        reply_markup=inline_builder_text(
                            text="Вернуться в меню", callback_data="main_menu"
                        ),
                    )
            else:
                await bot.send_message(
                    tg_id,
                    "Ваша машина вызвана на пропускной пункт.\n\n"
                    "<b>Счастливого пути!👋</b>",
                    reply_markup=inline_builder_text(
                        text="Вернуться в меню", callback_data="main_menu"
                    ),
                )

            # Очищаем состояние отслеживания в БД при завершении
            await req.clear_tracking(tg_id)
            break
        elif car_info is None:
            # Машина не найдена (прошла через ПП)

            # Проверяем, был ли куплен звонок, но еще не совершен
            if (call_info and
                call_info.get("call_purchased") and
                not call_info.get("call_completed") and
                    not call_made):
                # Отправляем звонок сразу, так как машина прошла
                phone_number = call_info.get("phone_number")
                if phone_number:
                    message = (
                        f"Ваша машина вызвана на пропускной пункт! "
                        f"Приготовьтесь к пропускному пункту."
                    )
                    call_sid = await make_call(phone_number, message, prevent_answer=True)

                    if call_sid:
                        await req.mark_call_completed(tg_id)
                        await bot.send_message(
                            tg_id,
                            f"<b>📞 Вам совершен телефонный звонок!</b>\n\n"
                            f"Ваша машина вызвана на пропускной пункт.\n\n"
                            f"<b>Счастливого пути!👋</b>\n\n"
                            f"Так же не забывайте переходить в нашу группу 😉",
                            reply_markup=inline_build_group_with_menu(
                                name="Попутчики 🙋 Водители 🚘",
                                url="tg://resolve?domain=travelersminsk",
                            ),
                        )
                    else:
                        await bot.send_message(
                            tg_id,
                            "Ваша машина вызвана на пропускной пункт.\n\n"
                            "<b>Счастливого пути!👋</b>\n\n"
                            "Так же не забывайте переходить в нашу группу 😉",
                            reply_markup=inline_build_group_with_menu(
                                name="Попутчики 🙋 Водители 🚘",
                                url="tg://resolve?domain=travelersminsk",
                            ),
                        )
                else:
                    await bot.send_message(
                        tg_id,
                        "Ваша машина вызвана на пропускной пункт.\n\n"
                        "<b>Счастливого пути!👋</b>\n\n"
                        "Так же не забывайте переходить в нашу группу 😉",
                        reply_markup=inline_build_group_with_menu(
                            name="Попутчики 🙋 Водители 🚘",
                            url="tg://resolve?domain=travelersminsk",
                        ),
                    )
            else:
                await bot.send_message(
                    tg_id,
                    "Ваша машина вызвана на пропускной пункт.\n\n"
                    "<b>Счастливого пути!👋</b>\n\n"
                    "Так же не забывайте переходить в нашу группу 😉",
                    reply_markup=inline_build_group_with_menu(
                        name="Попутчики 🙋 Водители 🚘",
                        url="tg://resolve?domain=travelersminsk",
                    ),
                )

            # Очищаем состояние отслеживания в БД при завершении
            await req.clear_tracking(tg_id)
            break
        else:
            pass

        await asyncio.sleep(interval * 60)
