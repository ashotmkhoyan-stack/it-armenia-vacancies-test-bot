"""
Модуль для хранения опубликованных вакансий и дедупликации.
"""
import aiosqlite
import hashlib
import logging
from datetime import datetime, timedelta

import config

logger = logging.getLogger(__name__)


def _make_fingerprint(url: str, title: str, company: str, location: str) -> str:
    """
    Создаёт уникальный отпечаток вакансии.
    Если URL есть — используем URL.
    Если нет — хэш из (title + company + location).
    """
    if url:
        key = url.strip().lower()
    else:
        key = f"{title}|{company}|{location}".strip().lower()
    return hashlib.sha256(key.encode()).hexdigest()


async def init_db(db_path: str = config.DATABASE_PATH) -> None:
    """Создаёт таблицы, если их нет."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS published_vacancies (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT    NOT NULL UNIQUE,
                url         TEXT,
                title       TEXT,
                company     TEXT,
                location    TEXT,
                source      TEXT,
                published_at TEXT   NOT NULL
            )
        """)
        await db.commit()
    logger.info("База данных инициализирована: %s", db_path)


async def is_duplicate(
    url: str,
    title: str,
    company: str,
    location: str,
    db_path: str = config.DATABASE_PATH,
) -> bool:
    """Проверяет, публиковалась ли уже эта вакансия."""
    fp = _make_fingerprint(url, title, company, location)
    ttl_date = (datetime.utcnow() - timedelta(days=config.DEDUP_TTL_DAYS)).isoformat()

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT 1 FROM published_vacancies WHERE fingerprint = ? AND published_at >= ?",
            (fp, ttl_date),
        )
        row = await cursor.fetchone()
    return row is not None


async def mark_published(
    url: str,
    title: str,
    company: str,
    location: str,
    source: str,
    db_path: str = config.DATABASE_PATH,
) -> None:
    """Записывает вакансию как опубликованную."""
    fp = _make_fingerprint(url, title, company, location)
    now = datetime.utcnow().isoformat()

    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO published_vacancies
                (fingerprint, url, title, company, location, source, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (fp, url, title, company, location, source, now),
        )
        await db.commit()
    logger.debug("Вакансия помечена как опубликованная: %s (%s)", title, url)


async def cleanup_old_records(db_path: str = config.DATABASE_PATH) -> None:
    """Удаляет записи старше TTL, чтобы база не пухла."""
    ttl_date = (datetime.utcnow() - timedelta(days=config.DEDUP_TTL_DAYS)).isoformat()
    async with aiosqlite.connect(db_path) as db:
        result = await db.execute(
            "DELETE FROM published_vacancies WHERE published_at < ?",
            (ttl_date,),
        )
        await db.commit()
        logger.info("Удалено устаревших записей: %d", result.rowcount)
