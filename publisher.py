"""
Публикует вакансии в Telegram-канал.
Включает проверку дедупликации и лимит на количество постов за один раз.
"""
import asyncio
import logging
from typing import List

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest

import config
import database
from formatter import format_vacancy
from vacancy import Vacancy

logger = logging.getLogger(__name__)

# Максимальная длина поста Telegram
MAX_TELEGRAM_LENGTH = 4096


async def publish_new_vacancies(bot: Bot, vacancies: List[Vacancy]) -> int:
    """
    Принимает список вакансий, фильтрует дубликаты и публикует новые.
    Возвращает количество опубликованных вакансий.
    """
    published_count = 0
    batch_limit = config.MAX_POSTS_PER_BATCH

    for vacancy in vacancies:
        if published_count >= batch_limit:
            logger.info(
                "Достигнут лимит батча (%d). Остальное — в следующий раз.",
                batch_limit,
            )
            break

        # Проверка дедупликации
        if await database.is_duplicate(
            url=vacancy.url,
            title=vacancy.title,
            company=vacancy.company,
            location=vacancy.location,
        ):
            logger.debug("Дубль пропущен: %s (%s)", vacancy.title, vacancy.url)
            continue

        # Форматирование
        text = format_vacancy(vacancy)

        # Telegram ограничивает сообщение 4096 символами
        if len(text) > MAX_TELEGRAM_LENGTH:
            text = text[: MAX_TELEGRAM_LENGTH - 20] + "\n\n<i>... [обрезано]</i>"

        # Публикация
        try:
            await bot.send_message(
                chat_id=config.CHANNEL_ID,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            await database.mark_published(
                url=vacancy.url,
                title=vacancy.title,
                company=vacancy.company,
                location=vacancy.location,
                source=vacancy.source,
            )
            published_count += 1
            logger.info("✅ Опубликовано: %s @ %s", vacancy.title, vacancy.company)

        except TelegramRetryAfter as e:
            logger.warning("Telegram flood control: ждём %d сек.", e.retry_after)
            await asyncio.sleep(e.retry_after)

        except TelegramBadRequest as e:
            logger.error("Telegram ошибка при публикации '%s': %s", vacancy.title, e)

        except Exception as e:
            logger.error("Неизвестная ошибка при публикации '%s': %s", vacancy.title, e)

        # Задержка между постами
        if published_count < batch_limit:
            await asyncio.sleep(config.DELAY_BETWEEN_POSTS)

    return published_count
