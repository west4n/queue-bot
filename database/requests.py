from sqlalchemy import select, func
from datetime import datetime

from database.models import async_session
from database.models import User, Payment, MenuContent


async def set_user(tg_id: int, name: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if not user:
            session.add(User(tg_id=tg_id, name=name))
            await session.commit()
            return True  # Новый пользователь
        return False  # Существующий пользователь


async def get_user(tg_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        return user


async def get_total_users():
    async with async_session() as session:
        total = await session.scalar(select(func.count(User.tg_id)))

        return total


async def set_car_number(tg_id: int, car_number: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if user.car_numbers is None:
            user.car_numbers = [car_number.upper()]
        else:
            user.car_numbers = user.car_numbers + [car_number.upper()]

        await session.commit()


async def set_active_car_number(tg_id: int, car_number: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if user:
            user.track_number = car_number.upper()
            await session.commit()


async def delete_car_number(tg_id: int, car_number: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if user and user.car_numbers:
            user.car_numbers = [
                number for number in user.car_numbers if number != car_number
            ]
            await session.commit()


async def get_users():
    async with async_session() as session:
        users = await session.execute(select(User.tg_id))

        return users.scalars().all()


async def set_tracking(tg_id: int, tracking_type: str, tracking_interval: int, initial_order_id: int = None):
    """Сохранение состояния отслеживания в БД"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if user:
            user.tracking_type = tracking_type
            user.tracking_interval = tracking_interval
            user.tracking_active = True
            if initial_order_id is not None:
                user.tracking_initial_order_id = initial_order_id
            await session.commit()


async def clear_tracking(tg_id: int):
    """Очистка состояния отслеживания в БД"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if user:
            user.tracking_type = None
            user.tracking_interval = None
            user.tracking_active = False
            user.tracking_initial_order_id = None
            # НЕ очищаем информацию о звонках - она сохраняется для повторного использования
            # Если пользователь снова запустит отслеживание, звонок сможет произойти
            await session.commit()


async def get_active_trackings():
    """Получение всех активных отслеживаний для восстановления"""
    async with async_session() as session:
        users = await session.execute(
            select(User).where(User.tracking_active == True)
        )

        return users.scalars().all()


async def update_tracking_initial_order_id(tg_id: int, initial_order_id: int):
    """Обновление initial_order_id без изменения других параметров отслеживания"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if user:
            user.tracking_initial_order_id = initial_order_id
            await session.commit()


async def set_call_info(tg_id: int, phone_number: str, queue_number: int, payment_charge_id: str):
    """Сохранение информации о покупке звонка"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if user:
            user.phone_number = phone_number
            user.call_queue_number = queue_number
            user.call_telegram_payment_charge_id = payment_charge_id
            user.call_purchased = True
            user.call_completed = False
            await session.commit()


async def get_call_info(tg_id: int):
    """Получение информации о звонке"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if user:
            return {
                "phone_number": user.phone_number,
                "call_queue_number": user.call_queue_number,
                "call_purchased": user.call_purchased,
                "call_completed": user.call_completed,
                "call_telegram_payment_charge_id": user.call_telegram_payment_charge_id,
            }
        return None


async def mark_call_completed(tg_id: int):
    """Отметка о совершенном звонке"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if user:
            user.call_completed = True
            await session.commit()


async def reset_call_info(tg_id: int):
    """Сброс информации о звонке (для повторной покупки)"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if user:
            user.phone_number = None
            user.call_queue_number = None
            user.call_purchased = False
            user.call_completed = False
            user.call_telegram_payment_charge_id = None
            await session.commit()


async def save_payment(tg_id: int, payment_charge_id: str, amount: int):
    """Сохранение успешного платежа"""
    async with async_session() as session:
        payment = Payment(
            tg_id=tg_id,
            payment_charge_id=payment_charge_id,
            amount=amount,
            payment_type="payment",
            created_at=datetime.utcnow()
        )
        session.add(payment)
        await session.commit()


async def save_refund(tg_id: int, payment_charge_id: str, amount: int):
    """Сохранение возврата"""
    async with async_session() as session:
        refund = Payment(
            tg_id=tg_id,
            payment_charge_id=payment_charge_id,
            amount=amount,
            payment_type="refund",
            created_at=datetime.utcnow()
        )
        session.add(refund)
        await session.commit()


async def get_payment_by_charge_id(payment_charge_id: str):
    """Получение платежа по payment_charge_id"""
    async with async_session() as session:
        payment = await session.scalar(
            select(Payment).where(
                Payment.payment_charge_id == payment_charge_id,
                Payment.payment_type == "payment"
            ).order_by(Payment.created_at.desc())
        )
        return payment


async def get_last_test_payment(tg_id: int):
    """Получение последнего тестового платежа для пользователя"""
    async with async_session() as session:
        payment = await session.scalar(
            select(Payment).where(
                Payment.tg_id == tg_id,
                Payment.payment_type == "payment",
                Payment.payment_charge_id.like("TEST_MODE_%")
            ).order_by(Payment.created_at.desc())
        )
        return payment


async def get_payment_statistics():
    """Получение статистики платежей"""
    async with async_session() as session:
        # Общее количество полученных звезд
        total_payments = await session.scalar(
            select(func.sum(Payment.amount)).where(
                Payment.payment_type == "payment")
        ) or 0

        # Общее количество возвращенных звезд
        total_refunds = await session.scalar(
            select(func.sum(Payment.amount)).where(
                Payment.payment_type == "refund")
        ) or 0

        # Чистая сумма
        net_amount = total_payments - total_refunds

        # Конвертация в доллары (1 звезда = 0.013$)
        STAR_TO_USD_RATE = 0.013
        usd_amount = net_amount * STAR_TO_USD_RATE

        return {
            "total_payments": total_payments,
            "total_refunds": total_refunds,
            "net_amount": net_amount,
            "usd_amount": usd_amount
        }


async def set_menu_content(key: str, chat_id: int, message_id: int):
    async with async_session() as session:
        content = await session.scalar(select(MenuContent).where(MenuContent.key == key))

        if content:
            content.source_chat_id = chat_id
            content.source_message_id = message_id
        else:
            session.add(
                MenuContent(
                    key=key,
                    source_chat_id=chat_id,
                    source_message_id=message_id,
                )
            )
        await session.commit()


async def get_menu_content(key: str):
    async with async_session() as session:
        return await session.scalar(select(MenuContent).where(MenuContent.key == key))
