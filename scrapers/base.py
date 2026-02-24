"""
Базовый класс для всех парсеров.
"""
import logging
from abc import ABC, abstractmethod
from typing import List

import aiohttp
from vacancy import Vacancy

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
}

# IT-ключевые слова для фильтрации
IT_KEYWORDS = {
    "developer", "dev", "engineer", "qa", "quality assurance", "tester",
    "devops", "sre", "data", "analyst", "data scientist", "ml", "ai",
    "machine learning", "backend", "frontend", "fullstack", "full-stack",
    "full stack", "mobile", "ios", "android", "react", "python", "java",
    "golang", "go", "node", "php", "ruby", "scala", "kotlin", "swift",
    "product manager", "product owner", "pm", "po", "scrum", "agile",
    "ux", "ui", "designer", "figma", "business analyst", "ba",
    "cybersecurity", "infosec", "architect", "cto", "ciso",
    "infrastructure", "cloud", "aws", "azure", "gcp", "kubernetes", "k8s",
    "tech lead", "team lead", "it", "software", "программист", "разработчик",
    "инженер", "тестировщик", "аналитик", "менеджер продукта",
}

# Локации для фильтрации
ARMENIA_LOCATIONS = {
    "armenia", "yerevan", "remote", "ереван", "армения", "հայաստան",
    "երևան", "hybrid", "distributed",
}


class BaseScraper(ABC):
    """Базовый класс парсера вакансий."""

    source_name: str = "unknown"

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def fetch_vacancies(self) -> List[Vacancy]:
        """Возвращает список вакансий с источника."""
        ...

    def is_it_vacancy(self, title: str, description: str = "") -> bool:
        """Проверяет, является ли вакансия IT-related."""
        text = f"{title} {description}".lower()
        return any(kw in text for kw in IT_KEYWORDS)

    def is_armenia_relevant(self, location: str, description: str = "") -> bool:
        """Проверяет релевантность вакансии для Армении."""
        text = f"{location} {description}".lower()
        return any(loc in text for loc in ARMENIA_LOCATIONS)

    def normalize_location(self, raw: str) -> str:
        """Нормализует строку локации к стандарту: Yerevan / Armenia / Remote / Hybrid."""
        low = raw.lower()
        if "remote" in low:
            return "Remote"
        if "hybrid" in low:
            return "Hybrid"
        if "yerevan" in low or "ереван" in low or "երևան" in low:
            return "Yerevan"
        if "armenia" in low or "армения" in low or "հայաստան" in low:
            return "Armenia"
        return raw.strip().title()

    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """GET-запрос с общими заголовками."""
        kwargs.setdefault("ssl", False)  # fix macOS SSL cert issue
        return await self.session.get(url, headers=HEADERS, **kwargs)
