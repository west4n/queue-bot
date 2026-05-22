import asyncio

from lexicon.lexicon import LEXICON_BUTTONS_BORDERS
from services.border_api import fetch_monitoring_data


async def find_my_car(car_number: str):
    """
    Поиск автомобиля по номеру во всех границах.
    Использует параллельные запросы для улучшения производительности.

    Args:
        car_number: Номер автомобиля для поиска

    Returns:
        Словарь с информацией о машине и границе или None
    """
    border_ids = list(LEXICON_BUTTONS_BORDERS.keys())

    # Выполняем параллельные запросы ко всем границам
    tasks = [fetch_monitoring_data(border_id) for border_id in border_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Обрабатываем результаты
    for border_id, data in zip(border_ids, results):
        # Пропускаем ошибки и None результаты
        if data is None or isinstance(data, Exception):
            continue

        # Ищем машину в очередях
        for queue_type in ["truckLiveQueue", "carLiveQueue", "busLiveQueue"]:
            queue = data.get(queue_type, [])

            for car in queue:
                if car["regnum"] == car_number:
                    return {
                        "car": car,
                        "border": {
                            "border_name": LEXICON_BUTTONS_BORDERS[border_id],
                            "border_key": border_id,
                        },
                    }

    return None
