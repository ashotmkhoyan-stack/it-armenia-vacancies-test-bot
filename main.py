"""
Точка входа приложения.

Запуск:
    python main.py

Что делает:
1. Инициализирует БД.
2. Запускает планировщик APScheduler.
3. Каждые SCRAPE_INTERVAL_MINUTES минут:
   - Собирает вакансии с hh.ru и staff.am
   - Фильтрует дубликаты
   - Публикует новые в Telegram-канал
"""
import asyncio
import logging
import sys
from typing import List

import aiohttp
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import config
import database
from publisher import publish_new_vacancies
from scrapers import HHruScraper, StaffAmScraper
from vacancy import Vacancy

# ─── Логирование ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("main")


# ─── Главная задача ─────────────────────────────────────────────────────────

async def scrape_and_publish(bot: Bot) -> None:
    # Не публикуем с 22:00 до 09:00
    from datetime import datetime
    hour = datetime.now().hour
    if hour >= 22 or hour < 9:
        logger.info("⏰ Тихий час (%d:xx) — публикация пропущена.", hour)
        return

    """
    Запускает все парсеры, собирает вакансии и публикует новые.
    Эта функция вызывается по расписанию.
    """
    logger.info("▶ Старт цикла сбора вакансий...")

    all_vacancies: List[Vacancy] = []

    # Один общий HTTP-сессия для всех парсеров
    connector = aiohttp.TCPConnector(limit=10)
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        scrapers = [
            HHruScraper(session),
            StaffAmScraper(session),
        ]

        for scraper in scrapers:
            try:
                vacancies = await scraper.fetch_vacancies()
                logger.info(
                    "  %s: получено %d вакансий", scraper.source_name, len(vacancies)
                )
                all_vacancies.extend(vacancies)
            except Exception as e:
                logger.error("  Ошибка парсера %s: %s", scraper.source_name, e)

    logger.info("Всего собрано: %d вакансий", len(all_vacancies))

    if not all_vacancies:
        logger.info("Нет новых вакансий — публикация пропущена.")
        return

    published = await publish_new_vacancies(bot, all_vacancies)
    logger.info("✅ Опубликовано новых вакансий: %d", published)

    # Раз в сутки чистим устаревшие записи
    await database.cleanup_old_records()


# ─── Запуск ─────────────────────────────────────────────────────────────────

async def main() -> None:
    # Инициализация БД
    await database.init_db()

    bot = Bot(token=config.BOT_TOKEN)

    # Проверка доступа к боту
    me = await bot.get_me()
    logger.info("Бот запущен: @%s (%s)", me.username, me.full_name)

    # Проверка доступа к каналу
    try:
        chat = await bot.get_chat(config.CHANNEL_ID)
        logger.info("Канал: %s (%s)", chat.title, config.CHANNEL_ID)
    except Exception as e:
        logger.error(
            "Не удалось получить инфо о канале %s: %s\n"
            "Убедитесь, что бот добавлен в канал как администратор.",
            config.CHANNEL_ID,
            e,
        )

    # Планировщик
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scrape_and_publish,
        trigger=IntervalTrigger(minutes=config.SCRAPE_INTERVAL_MINUTES),
        args=[bot],
        id="scrape_and_publish",
        replace_existing=True,
        max_instances=1,           # не запускать параллельно
        misfire_grace_time=60,     # пропустить если опоздал >60 сек
        coalesce=True,
    )
    scheduler.start()

    logger.info(
        "Планировщик запущен. Интервал: %d мин. Лимит батча: %d постов.",
        config.SCRAPE_INTERVAL_MINUTES,
        config.MAX_POSTS_PER_BATCH,
    )

    # Первый запуск — сразу при старте
    logger.info("Первый запуск — немедленно...")
    await scrape_and_publish(bot)

    # Держим event loop живым
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановка бота...")
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
