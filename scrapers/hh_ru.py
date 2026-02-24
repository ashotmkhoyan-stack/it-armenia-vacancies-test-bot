"""
Парсер hh.ru через официальный публичный API.
Документация: https://api.hh.ru/openapi/en/redoc

Area ID для Армении: 1365
"""
import logging
from typing import List, Optional

from scrapers.base import BaseScraper
from vacancy import Vacancy

logger = logging.getLogger(__name__)

HH_API_URL = "https://api.hh.ru/vacancies"
HH_VACANCY_URL = "https://api.hh.ru/vacancies/{id}"

# ID региона Армения в hh.ru
ARMENIA_AREA_ID = 1365

# Количество вакансий на страницу
PER_PAGE = 50


class HHruScraper(BaseScraper):
    """Парсер hh.ru через REST API."""

    source_name = "hh.ru"

    async def fetch_vacancies(self) -> List[Vacancy]:
        vacancies: List[Vacancy] = []

        # Профессиональные роли IT в hh.ru (можно расширить)
        # Полный список: https://api.hh.ru/professional_roles
        IT_ROLES = [
            "96",   # Программист, разработчик
            "160",  # Аналитик
            "10",   # Тестировщик
            "12",   # Технический директор
            "150",  # DevOps
            "25",   # Менеджер проекта (IT)
            "36",   # Data Scientist
            "73",   # Дизайнер (UX/UI)
            "164",  # Сетевой инженер
            "165",  # Системный администратор
        ]
        params = {
            "area": ARMENIA_AREA_ID,
            "per_page": PER_PAGE,
            "page": 0,
            "professional_role": IT_ROLES,
        }

        try:
            page = 0
            while True:
                params["page"] = page
                async with await self.get(HH_API_URL, params=params) as resp:
                    if resp.status != 200:
                        logger.warning("hh.ru API вернул статус %d", resp.status)
                        break
                    data = await resp.json()

                items = data.get("items", [])
                if not items:
                    break

                for item in items:
                    vacancy = await self._parse_item(item)
                    if vacancy:
                        vacancies.append(vacancy)

                total_pages = data.get("pages", 1)
                page += 1
                if page >= min(total_pages, 5):  # максимум 5 страниц за раз
                    break

        except Exception as e:
            logger.error("Ошибка при парсинге hh.ru: %s", e)

        logger.info("hh.ru: найдено %d вакансий", len(vacancies))
        return vacancies

    async def _parse_item(self, item: dict) -> Optional[Vacancy]:
        """Парсит краткую карточку и при необходимости загружает детали."""
        title = item.get("name", "")
        employer = (item.get("employer") or {}).get("name", "")
        area = (item.get("area") or {}).get("name", "")
        url = item.get("alternate_url", "")
        vacancy_id = item.get("id", "")

        location = self.normalize_location(area)

        if not self.is_it_vacancy(title):
            return None

        # Загружаем детали вакансии
        detail = await self._fetch_detail(vacancy_id)
        if not detail:
            return Vacancy(
                title=title,
                location=location,
                source=self.source_name,
                url=url,
                company=employer,
            )

        # Зарплата
        salary_raw = item.get("salary") or {}
        salary = self._format_salary(salary_raw)

        # Описание
        description_html = detail.get("description", "")
        description_text = _strip_html(description_html)

        # Ключевые навыки
        key_skills = [s.get("name", "") for s in detail.get("key_skills", [])]

        # Опыт и тип занятости
        experience = (detail.get("experience") or {}).get("name", "")
        schedule = (detail.get("schedule") or {}).get("name", "")
        employment = (detail.get("employment") or {}).get("name", "")

        grade = _extract_grade(title, experience)
        employment_type = _normalize_employment(employment, schedule)

        # Проект / описание
        snippet = (item.get("snippet") or {})
        project_context = snippet.get("responsibility") or description_text[:500]

        # Требования из description простейшим способом
        requirements_must = key_skills[:10]
        requirements_nice: List[str] = []

        return Vacancy(
            title=title,
            location=location,
            source=self.source_name,
            url=url,
            company=employer,
            grade=grade,
            employment_type=employment_type,
            working_language=_detect_language(description_html),
            project_context=project_context.strip(),
            responsibilities=_extract_bullets(description_html, "обязанност") or [],
            requirements_must=requirements_must,
            requirements_nice=requirements_nice,
            offer=_extract_bullets(description_html, "предлагаем") or [],
            salary=salary,
            contact=url,
        )

    async def _fetch_detail(self, vacancy_id: str) -> Optional[dict]:
        try:
            url = HH_VACANCY_URL.format(id=vacancy_id)
            async with await self.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.debug("Не удалось загрузить детали вакансии %s: %s", vacancy_id, e)
        return None

    def _format_salary(self, salary: dict) -> str:
        if not salary:
            return ""
        frm = salary.get("from")
        to = salary.get("to")
        currency = salary.get("currency", "")
        gross = "gross" if salary.get("gross") else "net"
        parts = []
        if frm:
            parts.append(f"от {frm}")
        if to:
            parts.append(f"до {to}")
        result = " ".join(parts)
        if currency:
            result += f" {currency}"
        if gross:
            result += f" ({gross})"
        return result.strip()


# ─── Вспомогательные функции ───────────────────────────────────────────────

def _strip_html(html: str) -> str:
    """Убирает HTML-теги из строки."""
    import re
    clean = re.sub(r"<[^>]+>", " ", html)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def _extract_grade(title: str, experience: str) -> str:
    low = f"{title} {experience}".lower()
    if "lead" in low or "principal" in low:
        return "Lead"
    if "senior" in low or "старший" in low:
        return "Senior"
    if "middle" in low or "mid" in low:
        return "Middle"
    if "junior" in low or "младший" in low:
        return "Junior"
    if "intern" in low or "стажёр" in low or "стажер" in low:
        return "Intern"
    if "1-3" in experience or "1–3" in experience:
        return "Middle"
    if "3-6" in experience or "3–6" in experience:
        return "Senior"
    return ""


def _normalize_employment(employment: str, schedule: str) -> str:
    low = f"{employment} {schedule}".lower()
    if "полная" in low or "full" in low:
        return "Full-time"
    if "частичная" in low or "part" in low:
        return "Part-time"
    if "проектная" in low or "contract" in low:
        return "Contract"
    return employment.strip()


def _detect_language(text: str) -> str:
    """Грубо определяет язык вакансии."""
    low = text.lower()
    has_en = any(w in low for w in ["english", "fluent", "upper-intermediate"])
    has_ru = any(w in low for w in ["русский", "russian", "на русском"])
    has_am = any(w in low for w in ["armenian", "հայerен", "армянский"])
    langs = []
    if has_en:
        langs.append("English")
    if has_ru:
        langs.append("Russian")
    if has_am:
        langs.append("Armenian")
    return ", ".join(langs) if langs else ""


def _extract_bullets(html: str, section_keyword: str) -> List[str]:
    """
    Грубо извлекает bullet-список из раздела HTML,
    содержащего section_keyword.
    """
    import re
    low = html.lower()
    idx = low.find(section_keyword)
    if idx == -1:
        return []
    chunk = html[idx: idx + 2000]
    items = re.findall(r"<li[^>]*>(.*?)</li>", chunk, re.DOTALL | re.IGNORECASE)
    return [_strip_html(i).strip() for i in items if i.strip()][:10]
