import logging
import asyncio
import time
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from config_data.config import Config, load_config

logger = logging.getLogger(__name__)
config: Config = load_config()


def _make_call_sync(phone_number: str, message: str, prevent_answer: bool = True) -> Optional[str]:
    """
    Синхронная функция для совершения звонка.

    Args:
        phone_number: Номер телефона для звонка
        message: Текст сообщения для звонка (не используется если prevent_answer=True)
        prevent_answer: Если True, звонок будет завершен через API после небольшой задержки,
                       чтобы телефон успел начать звонить, но пользователь не успел ответить.
                       Это гарантирует, что плата не будет взиматься (плата взимается только за отвеченные звонки).
                       Если False, звонок будет обычным с воспроизведением сообщения.
    """
    if not config.twilio.account_sid or not config.twilio.auth_token or not config.twilio.from_phone:
        logger.error("Twilio credentials not configured")
        return None

    try:
        client = Client(config.twilio.account_sid, config.twilio.auth_token)

        if prevent_answer:
            # Создаем звонок с пустым TwiML (звонок будет звонить, но ничего не воспроизведет)
            # Затем завершаем его через API через несколько секунд
            # Это дает время телефону начать звонить, но завершает звонок до того, как пользователь ответит
            twiml = '<Response><Pause length="1"/></Response>'
            logger.info(
                f"Creating call that will be hung up to prevent answer: {phone_number}")

            call = client.calls.create(
                to=phone_number,
                from_=config.twilio.from_phone,
                twiml=twiml
            )

            call_sid = call.sid
            hangup_delay = config.call_hangup_delay
            logger.info(
                f"Call initiated. Call SID: {call_sid}. Will hangup in {hangup_delay} seconds to prevent answer.")

            # Ждем указанное количество секунд, чтобы телефон успел начать звонить
            time.sleep(hangup_delay)

            # Завершаем звонок через API (отменяем звонок до ответа)
            try:
                call_instance = client.calls(call_sid)
                call_instance.update(status='canceled')
                logger.info(
                    f"Call {call_sid} canceled successfully to prevent answer")
            except Exception as hangup_error:
                logger.warning(
                    f"Could not cancel call {call_sid}: {hangup_error}. Call may have already ended.")

            return call_sid
        else:
            # Обычный звонок с воспроизведением сообщения
            twiml = f'<Response><Say language="ru-RU">{message}</Say></Response>'
            logger.info(f"Creating call with message playback: {phone_number}")

            call = client.calls.create(
                to=phone_number,
                from_=config.twilio.from_phone,
                twiml=twiml
            )

            logger.info(f"Call initiated successfully. Call SID: {call.sid}")
            return call.sid

    except TwilioRestException as e:
        logger.error(f"Twilio API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during call: {e}")
        return None


async def make_call(phone_number: str, message: str, prevent_answer: bool = True) -> Optional[str]:
    """
    Совершение звонка через Twilio (асинхронная обертка).
    В тестовом режиме также совершает реальные звонки через Twilio (только не требует оплату).

    Args:
        phone_number: Номер телефона для звонка (в формате E.164, например +375291234567)
        message: Текст сообщения для звонка (используется только если prevent_answer=False)
        prevent_answer: Если True, звонок будет завершен сразу после начала звонка,
                       чтобы пользователь не мог его поднять (не тратятся деньги).
                       По умолчанию True для экономии средств.
                       Если False, звонок будет обычным с воспроизведением сообщения.

    Returns:
        Call SID в случае успеха, None в случае ошибки

    Note:
        Twilio взимает плату только за отвеченные звонки (status: completed).
        Звонки со статусом no-answer, busy, failed, canceled - бесплатны.
        Использование prevent_answer=True гарантирует, что звонок не будет отвечен,
        и плата не будет взиматься.
    """
    # В обоих режимах совершаем реальные звонки через Twilio
    # Разница только в том, что в тестовом режиме не требуется оплата через Telegram Stars
    if config.call_mode == "test":
        logger.info(
            f"[TEST MODE] Making real call to {phone_number} (payment not required)")

    # Выполняем синхронный вызов Twilio в отдельном потоке, чтобы не блокировать event loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _make_call_sync, phone_number, message, prevent_answer)


def make_test_call(phone_number: str, message: str) -> Optional[str]:
    """
    Имитация звонка для тестового режима.

    Args:
        phone_number: Номер телефона для звонка
        message: Текст сообщения для звонка

    Returns:
        Тестовый Call SID
    """
    logger.info(
        f"[TEST MODE] Simulating call to {phone_number} with message: {message}")
    # Возвращаем тестовый SID
    return f"TEST_CALL_{phone_number}_{hash(message)}"
