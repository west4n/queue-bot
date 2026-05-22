from datetime import datetime, timedelta
from typing import Optional


def parse_registration_date(date_str: str) -> Optional[datetime]:
    """
    Парсит дату из формата API: "10:37:54 10.11.2025"

    Args:
        date_str: Строка с датой в формате "HH:MM:SS DD.MM.YYYY"

    Returns:
        datetime объект или None в случае ошибки парсинга
    """
    try:
        # Формат: "10:37:54 10.11.2025"
        return datetime.strptime(date_str, "%H:%M:%S %d.%m.%Y")
    except (ValueError, AttributeError):
        return None


def calculate_waiting_time(registration_date: datetime) -> dict[str, int]:
    """
    Рассчитывает время ожидания между регистрацией и текущим моментом.

    Args:
        registration_date: Дата регистрации

    Returns:
        Словарь с ключами: days, hours, minutes
    """
    now = datetime.now()
    delta = now - registration_date

    total_seconds = int(delta.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    return {
        "days": days,
        "hours": hours,
        "minutes": minutes
    }


def format_waiting_time(days: int, hours: int, minutes: int) -> str:
    """
    Форматирует время ожидания в читаемый формат.

    Args:
        days: Количество дней
        hours: Количество часов
        minutes: Количество минут

    Returns:
        Строка вида "4д 20ч 48мин"
    """
    parts = []
    if days > 0:
        parts.append(f"{days}д")
    if hours > 0:
        parts.append(f"{hours}ч")
    if minutes > 0:
        parts.append(f"{minutes}мин")

    return " ".join(parts) if parts else "0мин"


def count_priority_cars_last_24h(priority_queue: list) -> int:
    """
    Подсчитывает количество приоритетных машин, зарегистрированных за последние 24 часа.

    Args:
        priority_queue: Список машин из приоритетной очереди

    Returns:
        Количество машин, зарегистрированных за последние 24 часа
    """
    if not priority_queue:
        return 0

    now = datetime.now()
    cutoff_time = now - timedelta(hours=24)

    count = 0
    for car in priority_queue:
        registration_date_str = car.get("registration_date")
        if registration_date_str:
            reg_date = parse_registration_date(registration_date_str)
            if reg_date and reg_date >= cutoff_time:
                count += 1

    return count


def calculate_estimated_waiting_time(order_id: int, rate_per_hour: float) -> dict[str, int]:
    """
    Рассчитывает примерное время ожидания на основе позиции в очереди и темпа вызова.

    Args:
        order_id: Позиция в очереди (order_id первого авто)
        rate_per_hour: Темп вызова машин в час

    Returns:
        Словарь с ключами: days, hours, minutes
    """
    if rate_per_hour <= 0:
        return {"days": 0, "hours": 0, "minutes": 0}

    # Рассчитываем время в часах
    hours_needed = order_id / rate_per_hour

    # Преобразуем в дни, часы, минуты
    days = int(hours_needed // 24)
    hours = int(hours_needed % 24)
    minutes = int((hours_needed % 1) * 60)

    return {
        "days": days,
        "hours": hours,
        "minutes": minutes
    }
