import aiohttp
import asyncio
from typing import Optional


BASE_URL = "https://belarusborder.by/info"
TIMEOUT = aiohttp.ClientTimeout(total=10)


async def fetch_monitoring_data(border_id: str) -> Optional[dict]:
    """
    Получение данных мониторинга для указанной границы.

    Args:
        border_id: ID границы

    Returns:
        Словарь с данными мониторинга или None в случае ошибки
    """
    url = f"{BASE_URL}/monitoring-new?token=test&checkpointId={border_id}"

    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # Проверяем, что данные действительно словарь
                    if isinstance(data, dict):
                        return data
                    return None
                else:
                    return None
    except (aiohttp.ClientError, asyncio.TimeoutError):
        # В случае ошибки возвращаем None, чтобы не прерывать работу бота
        return None
    except Exception:
        # Обработка любых других ошибок (например, ошибки парсинга JSON)
        return None


async def fetch_statistics_data(border_id: str) -> Optional[dict]:
    """
    Получение статистики для указанной границы.

    Args:
        border_id: ID границы

    Returns:
        Словарь со статистикой или None в случае ошибки
    """
    url = f"{BASE_URL}/monitoring/statistics?token=test&checkpointId={border_id}"

    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # Проверяем, что данные действительно словарь
                    if isinstance(data, dict):
                        return data
                    return None
                else:
                    return None
    except (aiohttp.ClientError, asyncio.TimeoutError):
        # В случае ошибки возвращаем None, чтобы не прерывать работу бота
        return None
    except Exception:
        # Обработка любых других ошибок (например, ошибки парсинга JSON)
        return None
