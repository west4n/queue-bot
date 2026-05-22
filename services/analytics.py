"""
Сервис для логирования событий пользователей в аналитику
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from database.models import async_session, UserEvent

logger = logging.getLogger(__name__)


async def log_event(tg_id: int, event_type: str, event_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Логирование события пользователя в базу данных

    Args:
        tg_id: Telegram ID пользователя
        event_type: Тип события (start, add_car, delete_car, track_start, track_stop, etc.)
        event_data: Дополнительные данные события в виде словаря (опционально)

    Примечание:
        Функция асинхронная и не блокирует основной поток.
        Ошибки логируются, но не прерывают работу бота.
    """
    try:
        async with async_session() as session:
            event = UserEvent(
                tg_id=tg_id,
                event_type=event_type,
                event_data=event_data,
                created_at=datetime.utcnow()
            )
            session.add(event)
            await session.commit()
    except Exception as e:
        # Логируем ошибку, но не прерываем работу бота
        logger.error(
            f"Ошибка при логировании события {event_type} для пользователя {tg_id}: {e}")
