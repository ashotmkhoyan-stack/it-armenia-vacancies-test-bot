import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "@it_armenia_vacancies_test")
SCRAPE_INTERVAL_MINUTES: int = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "30"))
MAX_POSTS_PER_BATCH: int = int(os.getenv("MAX_POSTS_PER_BATCH", "5"))
DELAY_BETWEEN_POSTS: int = int(os.getenv("DELAY_BETWEEN_POSTS", "30"))
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "vacancies.db")
DEDUP_TTL_DAYS: int = int(os.getenv("DEDUP_TTL_DAYS", "60"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env файле!")
