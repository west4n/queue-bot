import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.types import CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from handlers import user, admin, my_cars, other, payment
from states import (
    add_car,
    queue_first_auto,
    queue_state,
    delete_car,
    state_mail,
    show_camera,
    buy_call,
    idea_state,
)

from config_data.config import Config, load_config

from database.models import async_main

from lexicon.lexicon import lexicon_buttons_minutes_keys, lexicon_buttons_cars_keys

from keyboards.kb_builder import inline_builder_text
from keyboards.start_menu import set_main_menu

from services.track_car_minutes import track_car_minutes
from services.track_car_queue import track_car_queue
from services.find_my_car import find_my_car
from services.analytics import log_event

import database.requests as req

logger = logging.getLogger(__name__)
config: Config = load_config()

bot = Bot(
    token=config.tg_bot.token, default=DefaultBotProperties(
        parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

tracking_tasks = {}


async def restore_trackings():
    """Восстановление всех активных отслеживаний из БД при старте бота"""
    try:
        active_users = await req.get_active_trackings()
        logger.info(f"Найдено активных отслеживаний: {len(active_users)}")

        for user in active_users:
            try:
                # Валидация данных
                if not user.track_number or not user.car_numbers:
                    logger.warning(
                        f"Пользователь {user.tg_id}: невалидные данные, очищаем отслеживание")
                    await req.clear_tracking(user.tg_id)
                    continue

                if user.track_number.upper() not in [num.upper() for num in user.car_numbers]:
                    logger.warning(
                        f"Пользователь {user.tg_id}: track_number не найден в car_numbers, очищаем отслеживание")
                    await req.clear_tracking(user.tg_id)
                    continue

                if user.tracking_type == "minutes":
                    # Восстановление отслеживания по времени
                    if user.tracking_interval:
                        # Проверяем информацию о звонках
                        call_info = await req.get_call_info(user.tg_id)
                        call_status = ""
                        if call_info and call_info.get("call_purchased"):
                            if call_info.get("call_completed"):
                                call_status = " (звонок уже совершен)"
                            else:
                                call_status = " (звонок активен, будет совершен при достижении очереди)"

                        task = asyncio.create_task(
                            track_car_minutes(
                                bot, user.tg_id, user.track_number, user.tracking_interval)
                        )
                        tracking_tasks[user.tg_id] = task
                        logger.info(
                            f"Восстановлено отслеживание по времени для пользователя {user.tg_id}, интервал: {user.tracking_interval} минут{call_status}")

                elif user.tracking_type == "queue":
                    # Восстановление отслеживания по количеству машин
                    car_info = await find_my_car(user.track_number)

                    if car_info is None:
                        logger.warning(
                            f"Пользователь {user.tg_id}: машина не найдена в очереди, очищаем отслеживание")
                        await req.clear_tracking(user.tg_id)
                        continue

                    if car_info["car"]["status"] != 2:
                        logger.warning(
                            f"Пользователь {user.tg_id}: машина не в очереди (status={car_info['car']['status']}), очищаем отслеживание")
                        await req.clear_tracking(user.tg_id)
                        continue

                    # Определяем начальный order_id
                    initial_order_id = user.tracking_initial_order_id
                    if initial_order_id is None:
                        order_id = car_info["car"].get("order_id")
                        if order_id is None:
                            logger.warning(
                                f"Пользователь {user.tg_id}: order_id отсутствует, очищаем отслеживание")
                            await req.clear_tracking(user.tg_id)
                            continue
                        initial_order_id = order_id
                        await req.update_tracking_initial_order_id(user.tg_id, initial_order_id)

                    if user.tracking_interval:
                        # Проверяем информацию о звонках
                        call_info = await req.get_call_info(user.tg_id)
                        call_status = ""
                        if call_info and call_info.get("call_purchased"):
                            if call_info.get("call_completed"):
                                call_status = " (звонок уже совершен)"
                            else:
                                call_status = " (звонок активен, будет совершен при достижении очереди)"

                        interval = 4  # Стандартный интервал проверки для отслеживания по количеству машин
                        task = asyncio.create_task(
                            track_car_queue(
                                bot, user.tg_id, user.track_number, user.tracking_interval, interval)
                        )
                        tracking_tasks[user.tg_id] = task
                        logger.info(
                            f"Восстановлено отслеживание по количеству машин для пользователя {user.tg_id}, интервал: {user.tracking_interval} машин{call_status}")

            except Exception as e:
                logger.error(
                    f"Ошибка при восстановлении отслеживания для пользователя {user.tg_id}: {e}")
                # Продолжаем восстановление остальных отслеживаний
                continue

        logger.info(
            f"Восстановление отслеживаний завершено. Активных задач: {len(tracking_tasks)}")
    except Exception as e:
        logger.error(
            f"Критическая ошибка при восстановлении отслеживаний: {e}")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(filename)s:%(lineno)d #%(levelname)-8s "
        "[%(asctime)s] - %(name)s - %(message)s",
    )
    logger.info("Starting Bot...")

    await async_main()
    await set_main_menu(bot)

    # Восстанавливаем все активные отслеживания из БД
    await restore_trackings()

    @dp.callback_query(F.data.in_(lexicon_buttons_minutes_keys))
    async def process_callback_track_minutes(callback: CallbackQuery):
        user = await req.get_user(callback.from_user.id)

        if callback.data == "5_min":
            interval = 5
        elif callback.data == "10_min":
            interval = 10
        else:
            interval = 15

        if user.tg_id in tracking_tasks:
            await callback.message.edit_text(
                "<b>У вас уже включены уведомления!</b>\n\n"
                "Сначала отключите имеющиеся уведомления или вернитесь в главное меню",
                reply_markup=inline_builder_text(
                    text=["Отменить уведомленя", "Вернуться в меню"],
                    callback_data=["remove_alert", "main_menu"],
                ),
            )
        else:
            # Проверяем наличие активного купленного звонка
            call_info = await req.get_call_info(callback.from_user.id)
            has_active_call = call_info and call_info.get("call_purchased") and not call_info.get("call_completed")

            if has_active_call:
                # У пользователя уже есть активный купленный звонок
                phone_number = call_info.get("phone_number", "не указан")
                queue_number = call_info.get("call_queue_number", "не указан")
                await callback.message.edit_text(
                    f"<b>Уведомления включены!</b>\n\n"
                    f"Уведомления будут приходить каждые <b>{interval}</b> минут\n\n"
                    f"📞 <b>У вас уже есть активный купленный звонок!</b>\n\n"
                    f"Номер телефона: <b>{phone_number}</b>\n"
                    f"Звонок поступит при очереди: <b>{queue_number}</b>\n\n"
                    f"Звонок будет автоматически совершен при достижении указанного номера очереди.",
                    reply_markup=inline_builder_text(
                        text="Запустить отслеживание",
                        callback_data=f"start_tracking:minutes:{interval}",
                    ),
                )
            else:
                # Показываем сообщение с кнопкой покупки звонка
                await callback.message.edit_text(
                    f"<b>Уведомления включены!</b>\n\n"
                    f"Уведомления будут приходить каждые <b>{interval}</b> минут\n\n"
                    f"Хотите получить дополнительный телефонный звонок при приближении очереди?",
                    reply_markup=inline_builder_text(
                        text=["Купить звонок", "Продолжить без звонка"],
                        callback_data=[
                            f"buy_call:minutes:{interval}", f"start_tracking:minutes:{interval}"],
                        sizes=[1, 1],
                    ),
                )

    @dp.callback_query(F.data.in_(lexicon_buttons_cars_keys))
    async def process_callback_track_cars(callback: CallbackQuery):
        user = await req.get_user(callback.from_user.id)

        if callback.data == "15_cars":
            cars = 15
        else:
            cars = 30

        interval = 4

        if user.tg_id in tracking_tasks:
            await callback.message.edit_text(
                "<b>У вас уже включены уведомления!</b>\n\n"
                "Сначала отключите имеющиеся уведомления или вернитесь в главное меню",
                reply_markup=inline_builder_text(
                    text=["Отменить уведомленя", "Вернуться в меню"],
                    callback_data=["remove_alert", "main_menu"],
                ),
            )
        else:
            # Проверяем наличие активного купленного звонка
            call_info = await req.get_call_info(callback.from_user.id)
            has_active_call = call_info and call_info.get("call_purchased") and not call_info.get("call_completed")

            if has_active_call:
                # У пользователя уже есть активный купленный звонок
                phone_number = call_info.get("phone_number", "не указан")
                queue_number = call_info.get("call_queue_number", "не указан")
                await callback.message.edit_text(
                    f"<b>Уведомления включены!</b>\n\n"
                    f"Уведомления будут приходить каждые <b>{cars}</b> машин\n\n"
                    f"📞 <b>У вас уже есть активный купленный звонок!</b>\n\n"
                    f"Номер телефона: <b>{phone_number}</b>\n"
                    f"Звонок поступит при очереди: <b>{queue_number}</b>\n\n"
                    f"Звонок будет автоматически совершен при достижении указанного номера очереди.",
                    reply_markup=inline_builder_text(
                        text="Запустить отслеживание",
                        callback_data=f"start_tracking:queue:{cars}",
                    ),
                )
            else:
                # Показываем сообщение с кнопкой покупки звонка
                await callback.message.edit_text(
                    f"<b>Уведомления включены!</b>\n\n"
                    f"Уведомления будут приходить каждые <b>{cars}</b> машин\n\n"
                    f"Хотите получить дополнительный телефонный звонок при приближении очереди?",
                    reply_markup=inline_builder_text(
                        text=["Купить звонок", "Продолжить без звонка"],
                        callback_data=[
                            f"buy_call:queue:{cars}", f"start_tracking:queue:{cars}"],
                        sizes=[1, 1],
                    ),
                )

    @dp.callback_query(F.data.startswith("start_tracking:"))
    async def process_callback_start_tracking(callback: CallbackQuery):
        """Запуск отслеживания без покупки звонка"""
        user_obj = await req.get_user(callback.from_user.id)

        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("Ошибка в данных", show_alert=True)
            return

        tracking_type = parts[1]
        interval_value = parts[2]

        if tracking_type == "minutes":
            interval = int(interval_value)
            await req.set_tracking(user_obj.tg_id, "minutes", interval)
            await log_event(user_obj.tg_id, "track_start", {
                "tracking_type": "minutes",
                "interval": interval,
                "car_number": user_obj.track_number
            })
            task = asyncio.create_task(
                track_car_minutes(bot, user_obj.tg_id,
                                  user_obj.track_number, interval)
            )
            tracking_tasks[user_obj.tg_id] = task
        elif tracking_type == "queue":
            cars = int(interval_value)
            poll_interval = 4
            await req.set_tracking(user_obj.tg_id, "queue", cars)
            await log_event(user_obj.tg_id, "track_start", {
                "tracking_type": "queue",
                "interval": cars,
                "car_number": user_obj.track_number
            })
            task = asyncio.create_task(
                track_car_queue(bot, user_obj.tg_id,
                                user_obj.track_number, cars, poll_interval)
            )
            tracking_tasks[user_obj.tg_id] = task

        await callback.answer("Отслеживание запущено!")

    @dp.callback_query(F.data == "remove_alert")
    async def process_callback_remove_alert(callback: CallbackQuery):
        # Проверяем, есть ли купленный звонок
        call_info = await req.get_call_info(callback.from_user.id)
        has_call = call_info and call_info.get(
            "call_purchased") and not call_info.get("call_completed")

        if has_call:
            # Если есть активный (не совершенный) звонок, показываем предупреждение
            await callback.message.edit_text(
                "<b>⚠️ Внимание!</b>\n\n"
                "У вас есть активный купленный звонок, который будет отменен.\n\n"
                "<b>Важно:</b> Средства за звонок не возвращаются.\n\n"
                "Вы уверены, что хотите отменить уведомления и звонок?",
                reply_markup=inline_builder_text(
                    text=["Да, отменить", "Нет, оставить"],
                    callback_data=["confirm_remove_alert",
                                   "cancel_remove_alert"],
                    sizes=[1, 1],
                ),
            )
            await callback.answer()
        else:
            # Если звонка нет или он уже совершен, просто отменяем
            task = tracking_tasks.get(callback.from_user.id)

            if task:
                task.cancel()
                del tracking_tasks[callback.from_user.id]

            # Очищаем состояние отслеживания в БД
            await req.clear_tracking(callback.from_user.id)
            await log_event(callback.from_user.id, "track_stop")

            # Если звонок был совершен ранее, очищаем информацию о нем
            if call_info and call_info.get("call_completed"):
                await req.reset_call_info(callback.from_user.id)

            await callback.message.edit_text(
                "Уведомления успешно отключены!",
                reply_markup=inline_builder_text(
                    text="Главное меню", callback_data="main_menu"
                ),
            )
            await callback.answer()

    @dp.callback_query(F.data == "confirm_remove_alert")
    async def process_callback_confirm_remove_alert(callback: CallbackQuery):
        """Подтверждение отмены уведомлений с активным звонком"""
        task = tracking_tasks.get(callback.from_user.id)

        if task:
            task.cancel()
            del tracking_tasks[callback.from_user.id]

        # Очищаем состояние отслеживания в БД
        await req.clear_tracking(callback.from_user.id)
        await log_event(callback.from_user.id, "track_stop", {"with_call_cancellation": True})

        # Отменяем звонок (очищаем информацию о звонке)
        await req.reset_call_info(callback.from_user.id)

        await callback.message.edit_text(
            "<b>Уведомления и звонок успешно отменены!</b>\n\n"
            "Информация о звонке удалена.",
            reply_markup=inline_builder_text(
                text="Главное меню", callback_data="main_menu"
            ),
        )
        await callback.answer()

    @dp.callback_query(F.data == "cancel_remove_alert")
    async def process_callback_cancel_remove_alert(callback: CallbackQuery):
        """Отмена удаления - возвращаемся к отслеживанию"""
        await callback.message.edit_text(
            "Отмена удаления. Отслеживание продолжается.",
            reply_markup=inline_builder_text(
                text="Отменить уведомления", callback_data="remove_alert"
            ),
        )
        await callback.answer()

    dp.include_router(admin.router)
    dp.include_router(user.router)
    dp.include_router(my_cars.router)
    dp.include_router(payment.router)

    dp.include_router(add_car.router)
    dp.include_router(queue_first_auto.router)
    dp.include_router(queue_state.router)
    dp.include_router(delete_car.router)
    dp.include_router(state_mail.router)
    dp.include_router(show_camera.router)
    dp.include_router(buy_call.router)
    dp.include_router(idea_state.router)

    dp.include_router(other.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped")
