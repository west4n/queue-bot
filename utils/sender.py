import asyncio

from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramRetryAfter

from typing import Dict, List


async def send_preview(message: Message, data: Dict) -> int:
    sent_message = await message.answer(
        text=f'{data["theme_text"]}\n\n' f'{data["message_text"]}'
    )

    message_id = sent_message.message_id

    return message_id


async def send_mail(bot: Bot, user_id: str, from_chat_id: int, message_id: int) -> bool:
    try:
        await bot.copy_message(
            chat_id=user_id, from_chat_id=from_chat_id, message_id=message_id
        )
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)

        return await send_mail(bot, user_id, from_chat_id, message_id)
    except Exception as e:
        print(e)
        return False
    else:
        return True


async def start_sender(
    bot: Bot, user_ids: List[str], from_chat_id: int, message_id: int
) -> int:
    count = 0
    for u_id in user_ids:
        if await send_mail(bot, u_id, from_chat_id, message_id):
            count += 1
        await asyncio.sleep(0.05)

    return count
