#!/usr/bin/env python3
"""
Скрипт для исследования данных очереди легковых автомобилей на границе Брест.

Рассчитывает следующие метрики:
1. Количество автомобилей в очереди
2. Количество вызванных машин за 24 часа
3. Темп вызова машин в час
4. Время ожидания первого автомобиля в очереди
5. Примерное время ожидания при регистрации в зоне ожидания сейчас
"""

from utils.queue_statistics import (
    parse_registration_date,
    calculate_waiting_time,
    format_waiting_time,
    count_priority_cars_last_24h,
    calculate_estimated_waiting_time,
)
from services.border_api import fetch_monitoring_data, fetch_statistics_data
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# ВАЖНО: Добавляем корневую директорию проекта в путь ПЕРЕД импортами локальных модулей
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Теперь импортируем локальные модули проекта (после добавления пути!)


# ID границы Брест
BREST_CHECKPOINT_ID = "a9173a85-3fc0-424c-84f0-defa632481e4"
CHECKPOINT_NAME = "Брест"


def calculate_all_metrics(
    monitoring_data: Dict[str, Any],
    statistics_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Рассчитывает все метрики на основе данных мониторинга и статистики.

    Args:
        monitoring_data: Данные из API мониторинга
        statistics_data: Данные из API статистики

    Returns:
        Словарь со всеми рассчитанными метриками
    """
    metrics = {}

    # Получаем очередь легковых автомобилей
    car_live_queue = monitoring_data.get("carLiveQueue", [])
    car_priority_queue = monitoring_data.get("carPriority", [])

    # Метрика 1: Количество автомобилей в очереди
    # Фильтруем только машины со статусом 2 (в очереди с order_id)
    cars_in_queue = [car for car in car_live_queue if car.get("status") == 2]
    metrics["cars_in_queue"] = len(cars_in_queue)

    # Метрика 2: Вызвано машин за 24 часа и за последний час
    # Получаем данные из API статистики
    called_last_day = int(statistics_data.get("carLastDay", 0))
    called_last_hour = int(statistics_data.get("carLastHour", 0))
    priority_last_24h = count_priority_cars_last_24h(car_priority_queue)

    # Подсчет вызванных машин за последний час из очереди
    from datetime import timedelta
    now = datetime.now()
    cutoff_time_24h = now - timedelta(hours=24)
    cutoff_time_1h = now - timedelta(hours=1)

    # Подсчет за последний час из очереди
    called_from_queue_1h = 0
    for car in car_live_queue:
        status = car.get("status")
        changed_date_str = car.get("changed_date")
        # Считаем машины со статусом 3 (вызванные) или 9 (обработанные)
        if status in [3, 9] and changed_date_str:
            changed_date = parse_registration_date(changed_date_str)
            if changed_date and changed_date >= cutoff_time_1h:
                called_from_queue_1h += 1

    # Альтернативный подсчет за 24 часа: считаем машины со статусом 3 (вызванные) и 9 (обработанные)
    # из очереди, которые были изменены за последние 24 часа
    called_from_queue_24h = 0
    for car in car_live_queue:
        status = car.get("status")
        changed_date_str = car.get("changed_date")
        # Считаем машины со статусом 3 (вызванные) или 9 (обработанные)
        if status in [3, 9] and changed_date_str:
            changed_date = parse_registration_date(changed_date_str)
            if changed_date and changed_date >= cutoff_time_24h:
                called_from_queue_24h += 1

    total_called_24h = called_last_day + priority_last_24h

    # Отладочная информация: все доступные поля статистики и альтернативный подсчет
    debug_stats = {
        "carLastHour": called_last_hour,
        "carLastDay": called_last_day,
        "all_statistics_fields": {k: v for k, v in statistics_data.items() if k.startswith("car")},
        "alternative_count_from_queue_24h": called_from_queue_24h,
        "alternative_count_from_queue_1h": called_from_queue_1h,
        "difference_24h": called_from_queue_24h - called_last_day
    }

    metrics["called_last_24h"] = {
        "regular": called_last_day,
        "priority": priority_last_24h,
        "total": total_called_24h,
        "debug": debug_stats
    }

    # Метрика 2.5: Вызвано машин за последний час
    metrics["called_last_hour"] = {
        "from_api": called_last_hour,
        "from_queue": called_from_queue_1h,
        "note": "from_api - данные из API статистики, from_queue - подсчет из текущей очереди (может быть меньше, т.к. обработанные машины удаляются)"
    }

    # Метрика 3: Темп вызова машин в час
    rate_per_hour = round(total_called_24h / 24,
                          2) if total_called_24h > 0 else 0.0
    metrics["rate_per_hour"] = rate_per_hour

    # Метрика 4: Время ожидания первого автомобиля
    first_car_info = {}
    if cars_in_queue:
        first_car = cars_in_queue[0]
        registration_date_str = first_car.get("registration_date", "")
        changed_date_str = first_car.get("changed_date", "")
        order_id = first_car.get("order_id")

        reg_date = parse_registration_date(registration_date_str)
        changed_date = parse_registration_date(
            changed_date_str) if changed_date_str else None

        if reg_date:
            waiting_time = calculate_waiting_time(reg_date)
            waiting_time_str = format_waiting_time(
                waiting_time["days"],
                waiting_time["hours"],
                waiting_time["minutes"]
            )

            first_car_info = {
                "regnum": first_car.get("regnum", "N/A"),
                "order_id": order_id,
                "registration_date": registration_date_str,
                "waiting_time": waiting_time,
                "waiting_time_formatted": waiting_time_str,
            }

            # Проверяем, когда машина стала первой
            if changed_date and changed_date != reg_date:
                # changed_date отличается от registration_date - возможно, это момент изменения позиции
                time_to_first = calculate_waiting_time(changed_date)
                first_car_info["became_first_at"] = changed_date_str
                first_car_info["time_to_first"] = time_to_first
                first_car_info["time_to_first_formatted"] = format_waiting_time(
                    time_to_first["days"],
                    time_to_first["hours"],
                    time_to_first["minutes"]
                )
            else:
                # changed_date совпадает с registration_date или отсутствует
                # Без исторических данных невозможно точно определить, когда машина стала первой
                first_car_info["became_first_at"] = None
                first_car_info["note"] = "Точное время, когда машина стала первой, недоступно без исторических данных"
        else:
            first_car_info = {
                "error": "Не удалось распарсить дату регистрации",
                "registration_date": registration_date_str
            }
    else:
        first_car_info = {
            "error": "Нет машин в очереди"
        }

    metrics["first_car_waiting"] = first_car_info

    # Метрика 5: Примерное время ожидания при регистрации сейчас
    # Используем общее количество машин в очереди, а не order_id первого автомобиля
    # Если сейчас в очереди N машин, то новый автомобиль будет (N+1)-м
    estimated_waiting = {}
    if cars_in_queue and rate_per_hour > 0:
        # Используем общее количество машин в очереди
        total_cars = len(cars_in_queue)
        # Новый автомобиль будет следующим в очереди
        new_car_position = total_cars + 1

        estimated = calculate_estimated_waiting_time(
            new_car_position, rate_per_hour)
        estimated_str = format_waiting_time(
            estimated["days"],
            estimated["hours"],
            estimated["minutes"]
        )
        estimated_waiting = {
            "current_queue_size": total_cars,
            "new_car_position": new_car_position,
            "rate_per_hour": rate_per_hour,
            "estimated_time": estimated,
            "estimated_time_formatted": estimated_str,
            "calculation_time": datetime.now().strftime("%d.%m.%Y %H:%M")
        }
    else:
        if not cars_in_queue:
            estimated_waiting = {"error": "Нет машин в очереди"}
        else:
            estimated_waiting = {
                "error": "Невозможно рассчитать (темп вызова = 0)"}

    metrics["estimated_waiting_now"] = estimated_waiting

    return metrics


def format_console_output(metrics: Dict[str, Any]) -> str:
    """
    Форматирует метрики для красивого вывода в консоль.

    Args:
        metrics: Словарь с метриками

    Returns:
        Отформатированная строка для вывода
    """
    output = []
    output.append("=" * 60)
    output.append(f"ИССЛЕДОВАНИЕ ОЧЕРЕДИ НА ГРАНИЦЕ: {CHECKPOINT_NAME}")
    output.append("=" * 60)
    output.append("")

    # Метрика 1
    output.append("1. КОЛИЧЕСТВО АВТОМОБИЛЕЙ В ОЧЕРЕДИ")
    output.append(f"   {metrics['cars_in_queue']} автомобилей")
    output.append("")

    # Метрика 2
    output.append("2. ВЫЗВАНО МАШИН ЗА 24 ЧАСА")
    called_info = metrics['called_last_24h']
    output.append(f"   Обычных: {called_info['regular']}")
    output.append(f"   Приоритетных: {called_info['priority']}")
    output.append(f"   Всего: {called_info['total']}")
    output.append("")

    # Метрика 2.5: Вызвано машин за последний час
    output.append("2.5. ВЫЗВАНО МАШИН ЗА ПОСЛЕДНИЙ ЧАС")
    called_hour_info = metrics.get('called_last_hour', {})
    output.append(
        f"   Из API статистики: {called_hour_info.get('from_api', 'N/A')}")
    output.append(
        f"   Из очереди: {called_hour_info.get('from_queue', 'N/A')}")
    if called_hour_info.get('note'):
        output.append(f"   ({called_hour_info.get('note', '')})")
    output.append("")

    # Метрика 3
    output.append("3. ТЕМП ВЫЗОВА МАШИН В ЧАС")
    output.append(f"   {metrics['rate_per_hour']} машин/час")
    output.append("")

    # Метрика 4
    output.append("4. ВРЕМЯ ОЖИДАНИЯ ПЕРВОГО АВТОМОБИЛЯ В ОЧЕРЕДИ")
    first_car = metrics['first_car_waiting']
    if "error" in first_car:
        output.append(f"   Ошибка: {first_car['error']}")
    else:
        output.append(f"   Номер: {first_car.get('regnum', 'N/A')}")
        output.append(
            f"   Позиция в очереди: {first_car.get('order_id', 'N/A')}")
        output.append(
            f"   Дата регистрации: {first_car.get('registration_date', 'N/A')}")
        output.append(
            f"   Время ожидания: {first_car.get('waiting_time_formatted', 'N/A')}")

        if first_car.get("became_first_at"):
            output.append(
                f"   Стал первым: {first_car.get('became_first_at', 'N/A')}")
            output.append(
                f"   Время до первого места: {first_car.get('time_to_first_formatted', 'N/A')}")
        elif first_car.get("note"):
            output.append(f"   Примечание: {first_car.get('note', '')}")
    output.append("")

    # Метрика 5
    output.append("5. ПРИМЕРНОЕ ВРЕМЯ ОЖИДАНИЯ ПРИ РЕГИСТРАЦИИ СЕЙЧАС")
    estimated = metrics['estimated_waiting_now']
    if "error" in estimated:
        output.append(f"   Ошибка: {estimated['error']}")
    else:
        output.append(
            f"   Машин в очереди сейчас: {estimated.get('current_queue_size', 'N/A')}")
        output.append(
            f"   Позиция нового автомобиля: {estimated.get('new_car_position', 'N/A')}")
        output.append(
            f"   Темп вызова: {estimated.get('rate_per_hour', 'N/A')} машин/час")
        output.append(
            f"   Примерное время ожидания: {estimated.get('estimated_time_formatted', 'N/A')}")
        output.append(
            f"   Время расчета: {estimated.get('calculation_time', 'N/A')}")
    output.append("")

    output.append("=" * 60)

    return "\n".join(output)


def save_to_json(metrics: Dict[str, Any], output_dir: Path) -> Path:
    """
    Сохраняет метрики в JSON файл.

    Args:
        metrics: Словарь с метриками
        output_dir: Директория для сохранения результатов

    Returns:
        Путь к сохраненному файлу
    """
    # Создаем директорию, если её нет
    output_dir.mkdir(parents=True, exist_ok=True)

    # Формируем имя файла с timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"brest_queue_{timestamp}.json"
    filepath = output_dir / filename

    # Подготавливаем данные для сохранения
    result_data = {
        "timestamp": datetime.now().isoformat(),
        "checkpoint_id": BREST_CHECKPOINT_ID,
        "checkpoint_name": CHECKPOINT_NAME,
        "metrics": metrics
    }

    # Сохраняем в JSON
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    return filepath


async def main():
    """
    Основная функция для запуска исследования.
    """
    print("Запуск исследования очереди на границе Брест...")
    print("")

    # Получаем данные из API
    print("Получение данных из API...")
    monitoring_data, statistics_data = await asyncio.gather(
        fetch_monitoring_data(BREST_CHECKPOINT_ID),
        fetch_statistics_data(BREST_CHECKPOINT_ID)
    )

    # Проверка на ошибки
    if monitoring_data is None:
        print("ОШИБКА: Не удалось получить данные мониторинга")
        return

    if statistics_data is None:
        print("ОШИБКА: Не удалось получить данные статистики")
        return

    print("Данные успешно получены")
    print("")

    # Рассчитываем метрики
    print("Расчет метрик...")
    metrics = calculate_all_metrics(monitoring_data, statistics_data)

    # Выводим результаты в консоль
    console_output = format_console_output(metrics)
    print(console_output)

    # Сохраняем результаты в JSON
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "research_results"
    json_filepath = save_to_json(metrics, output_dir)
    print(f"\nРезультаты сохранены в файл: {json_filepath}")


if __name__ == "__main__":
    asyncio.run(main())
