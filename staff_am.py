"""
Парсер staff.am — крупнейшая армянская платформа для поиска работы.
"""
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from vacancy import Vacancy

logger = logging.getLogger(__name__)

BASE_URL = "https://staff.am"
JOBS_URL = "https://staff.am/en/jobs"


class StaffAmScraper(BaseScraper):
    """Парсер staff.am."""

    source_name = "staff.am"

    async def fetch_vacancies(self) -> List[Vacancy]:
        vacancies: List[Vacancy] = []

        try:
            page = 1
            while page <= 5:  # максимум 5 страниц за раз
                url = f"{JOBS_URL}?page={page}"
                async with await self.get(url) as resp:
                    if resp.status != 200:
                        logger.warning("staff.am: статус %d на стр. %d", resp.status, page)
                        break
                    html = await resp.text()

                soup = BeautifulSoup(html, "lxml")
                cards = soup.select("div.job-item, article.job-item, div.job-list-item, li.job-item")

                # Если не нашли по первому селектору — пробуем шире
                if not cards:
                    cards = soup.select("[class*='job-item'], [class*='vacancy-item']")

                if not cards:
                    logger.debug("staff.am стр. %d: карточки не найдены, выходим.", page)
                    break

                for card in cards:
                    vacancy = self._parse_card(card)
                    if vacancy:
                        vacancies.append(vacancy)

                # Проверяем кнопку «следующая страница»
                next_btn = soup.select_one("a[rel='next'], a.next, .pagination .next")
                if not next_btn:
                    break
                page += 1

        except Exception as e:
            logger.error("Ошибка при парсинге staff.am: %s", e)

        logger.info("staff.am: найдено %d вакансий", len(vacancies))
        return vacancies

    def _parse_card(self, card) -> Optional[Vacancy]:
        """Парсит карточку вакансии со страницы списка."""
        try:
            # Заголовок
            title_el = (
                card.select_one("h2 a, h3 a, .job-title a, .vacancy-title a, a.title")
                or card.select_one("a[href*='/jobs/'], a[href*='/vacancies/']")
            )
            if not title_el:
                return None

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url = urljoin(BASE_URL, href) if href else ""

            if not self.is_it_vacancy(title):
                return None

            # Компания
            company_el = card.select_one(".company-name, .employer-name, [class*='company']")
            company = company_el.get_text(strip=True) if company_el else ""

            # Локация
            location_el = card.select_one(".location, [class*='location'], [class*='city']")
            raw_location = location_el.get_text(strip=True) if location_el else "Armenia"
            location = self.normalize_location(raw_location)

            if not self.is_armenia_relevant(raw_location):
                return None

            # Тип занятости
            type_el = card.select_one(".employment-type, [class*='employment'], [class*='type']")
            employment_type = type_el.get_text(strip=True) if type_el else ""

            return Vacancy(
                title=title,
                location=location,
                source=self.source_name,
                url=url,
                company=company,
                employment_type=employment_type,
                contact=url,
            )

        except Exception as e:
            logger.debug("Ошибка парсинга карточки staff.am: %s", e)
            return None

    async def fetch_detail(self, vacancy: Vacancy) -> Vacancy:
        """
        Загружает страницу вакансии и обогащает объект деталями.
        Вызывать опционально для получения полных данных.
        """
        if not vacancy.url:
            return vacancy
        try:
            async with await self.get(vacancy.url) as resp:
                if resp.status != 200:
                    return vacancy
                html = await resp.text()

            soup = BeautifulSoup(html, "lxml")

            # Описание
            desc_el = soup.select_one(
                ".job-description, .vacancy-description, [class*='description'], article"
            )
            if desc_el:
                text = desc_el.get_text(separator="\n", strip=True)
                vacancy.project_context = _first_paragraph(text, max_chars=600)
                vacancy.responsibilities = _extract_section(text, [
                    "responsibilities", "duties", "what you'll do",
                    "обязанности", "задачи"
                ])
                vacancy.requirements_must = _extract_section(text, [
                    "requirements", "qualifications", "must have",
                    "требования", "обязательно"
                ])
                vacancy.requirements_nice = _extract_section(text, [
                    "nice to have", "nice-to-have", "preferred", "plus",
                    "будет плюсом"
                ])
                vacancy.offer = _extract_section(text, [
                    "we offer", "what we offer", "benefits", "условия",
                    "мы предлагаем"
                ])
                vacancy.working_language = _detect_language_in_text(text)

            # Зарплата
            salary_el = soup.select_one(".salary, [class*='salary']")
            if salary_el:
                vacancy.salary = salary_el.get_text(strip=True)

            # Контакт
            contact_el = soup.select_one("a[href^='mailto:'], a[href^='tg:'], a[href*='t.me']")
            if contact_el:
                vacancy.contact = contact_el.get("href", "") or contact_el.get_text(strip=True)

        except Exception as e:
            logger.debug("Ошибка загрузки деталей staff.am %s: %s", vacancy.url, e)

        return vacancy


# ─── Вспомогательные функции ────────────────────────────────────────────────

def _first_paragraph(text: str, max_chars: int = 500) -> str:
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 30]
    result = ""
    for line in lines[:4]:
        result += line + " "
        if len(result) >= max_chars:
            break
    return result.strip()[:max_chars]


def _extract_section(text: str, keywords: List[str]) -> List[str]:
    """Ищет секцию по ключевым словам и извлекает пункты списка."""
    low = text.lower()
    for kw in keywords:
        idx = low.find(kw)
        if idx == -1:
            continue
        chunk = text[idx: idx + 1500]
        lines = chunk.split("\n")[1:]  # пропускаем строку-заголовок
        bullets = []
        for line in lines:
            line = line.strip().lstrip("•-–*▪►→").strip()
            if not line:
                continue
            # Останавливаемся при встрече следующего заголовка
            if any(kw2 in line.lower() for kw2 in [
                "responsibilities", "requirements", "we offer",
                "обязанности", "требования", "предлагаем",
                "nice to have", "must have"
            ]):
                break
            if 3 < len(line) < 300:
                bullets.append(line)
            if len(bullets) >= 10:
                break
        if bullets:
            return bullets
    return []


def _detect_language_in_text(text: str) -> str:
    low = text.lower()
    langs = []
    if any(w in low for w in ["english", "fluent", "upper-intermediate", "b2", "c1"]):
        langs.append("English")
    if any(w in low for w in ["russian", "русский", "ru level"]):
        langs.append("Russian")
    if any(w in low for w in ["armenian", "հայerен"]):
        langs.append("Armenian")
    return ", ".join(langs) if langs else ""
