"""
Парсер staff.am — данные из __NEXT_DATA__ -> pageProps.jobs
"""
import json
import logging
import re
from typing import List, Optional

from scrapers.base import BaseScraper
from vacancy import Vacancy

logger = logging.getLogger(__name__)

BASE_URL = "https://staff.am"
JOBS_URL = "https://staff.am/en/jobs"

NON_IT_CATEGORIES = {
    "bookkeeping", "banking", "sales-management", "construction",
    "medicine", "legal", "hospitality", "manufacturing", "logistics",
    "agriculture", "beauty", "security", "journalism", "real-estate",
    "transportation", "other-services", "cleaning", "driving",
}


class StaffAmScraper(BaseScraper):
    source_name = "staff.am"

    async def fetch_vacancies(self) -> List[Vacancy]:
        vacancies: List[Vacancy] = []
        try:
            page = 1
            while page <= 5:
                url = f"{JOBS_URL}?page={page}"
                async with await self.get(url) as resp:
                    if resp.status != 200:
                        break
                    html = await resp.text()

                data = _extract_next_data(html)
                if not data:
                    break

                page_props = data.get("props", {}).get("pageProps", {})
                jobs = page_props.get("jobs", [])
                total_count = page_props.get("totalCount", 0)

                if not jobs:
                    break

                logger.info("staff.am стр.%d: вакансий %d, всего %d", page, len(jobs), total_count)

                for job in jobs:
                    vacancy = _parse_job(job)
                    if vacancy and self.is_it_vacancy(vacancy.title):
                        vacancy = await self._fetch_detail(vacancy)
                        vacancies.append(vacancy)

                total_pages = (total_count // 52) + 1
                if page >= min(total_pages, 5):
                    break
                page += 1

        except Exception as e:
            logger.error("Ошибка staff.am: %s", e, exc_info=True)

        logger.info("staff.am: итого IT-вакансий %d", len(vacancies))
        return vacancies

    async def _fetch_detail(self, vacancy: Vacancy) -> Vacancy:
        """Загружает детали вакансии со страницы."""
        if not vacancy.url:
            return vacancy
        try:
            async with await self.get(vacancy.url) as resp:
                if resp.status != 200:
                    return vacancy
                html = await resp.text()

            data = _extract_next_data(html)
            if not data:
                return vacancy

            page_props = data.get("props", {}).get("pageProps", {})
            job_data = (
                page_props.get("job")
                or page_props.get("vacancy")
                or page_props.get("jobDetail")
                or {}
            )
            if job_data:
                vacancy = _enrich_from_data(vacancy, job_data)

        except Exception as e:
            logger.debug("Ошибка деталей %s: %s", vacancy.url, e)

        return vacancy


# ─── Функции вне класса ─────────────────────────────────────────────────────

def _extract_next_data(html: str) -> Optional[dict]:
    match = re.search(
        r'<script\s+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _parse_job(job: dict) -> Optional[Vacancy]:
    try:
        # Заголовок
        title_raw = job.get("title", {})
        title = (title_raw.get("en") or title_raw.get("am_en") or title_raw.get("ru") or "") \
            if isinstance(title_raw, dict) else str(title_raw)
        if not title:
            return None

        # Категория
        # Категория — используем поле code для URL
        category_raw = job.get("category", {})
        if isinstance(category_raw, dict):
            category_code = category_raw.get("code") or category_raw.get("slug") or ""
        else:
            category_code = str(category_raw)

        if category_code in NON_IT_CATEGORIES:
            return None

        # Slug — словарь {en, ru, am}
        slug_raw = job.get("slug", "")
        slug = (slug_raw.get("en") or slug_raw.get("ru") or slug_raw.get("am") or "") \
            if isinstance(slug_raw, dict) else str(slug_raw)

        job_id = job.get("id", "")
        if slug and category_code:
            url = f"{BASE_URL}/en/jobs/{category_code}/{slug}"
        elif slug:
            url = f"{BASE_URL}/en/jobs/{slug}"
        elif job_id:
            url = f"{BASE_URL}/en/jobs/{job_id}"
        else:
            url = ""

        # Локация
        is_remote = job.get("is_remote", False)
        city_raw = job.get("job_city", {})
        if is_remote:
            location = "Remote"
        elif isinstance(city_raw, dict):
            city_title = city_raw.get("title", {})
            city = (city_title.get("en") or city_title.get("ru") or "") \
                if isinstance(city_title, dict) else str(city_title)
            location = _normalize_location(city)
        else:
            location = "Armenia"

        # Компания — может быть dict или list
        companies = job.get("companiesStruct", {})
        company = ""
        if isinstance(companies, dict):
            title_raw = companies.get("title", {})
            if isinstance(title_raw, dict):
                company = title_raw.get("en") or title_raw.get("ru") or ""
            else:
                company = companies.get("name") or companies.get("title") or ""
        elif isinstance(companies, list) and companies:
            c = companies[0]
            if isinstance(c, dict):
                title_raw = c.get("title", {})
                company = (title_raw.get("en") if isinstance(title_raw, dict) else "") or c.get("name") or ""

        return Vacancy(
            title=title,
            location=location,
            source="staff.am",
            url=url,
            company=company,
            contact=url,
        )

    except Exception as e:
        logger.debug("Ошибка парсинга job: %s", e)
        return None


def _enrich_from_data(vacancy: Vacancy, data: dict) -> Vacancy:
    try:
        def get_en(field) -> str:
            """Берёт английскую версию из {en, ru, am} или возвращает строку."""
            if isinstance(field, dict):
                return field.get("en") or field.get("ru") or field.get("am") or ""
            return str(field) if field else ""

        def clean_html(text: str) -> str:
            t = re.sub(r"<[^>]+>", " ", text)
            return re.sub(r"\s+", " ", t).strip()

        # Описание
        desc = get_en(data.get("description") or "")
        if desc:
            vacancy.project_context = clean_html(desc)[:500]
            low = desc.lower()
            langs = []
            if any(w in low for w in ["english", "fluent", "b2", "c1", "upper-intermediate"]):
                langs.append("English")
            if "russian" in low:
                langs.append("Russian")
            if "armenian" in low:
                langs.append("Armenian")
            vacancy.working_language = ", ".join(langs)

        # Обязанности — отдельное поле
        resp_raw = data.get("responsibilities") or ""
        resp_text = get_en(resp_raw)
        if resp_text:
            resp_clean = clean_html(resp_text)
            vacancy.responsibilities = _extract_bullets(resp_clean)

        # Требования — отдельное поле
        req_raw = data.get("required_qualifications") or ""
        req_text = get_en(req_raw)
        if req_text:
            req_clean = clean_html(req_text)
            vacancy.requirements_must = _extract_bullets(req_clean)

        # Навыки как must have (если нет требований)
        if not vacancy.requirements_must:
            skills = data.get("skills") or []
            if isinstance(skills, list):
                vacancy.requirements_must = [
                    get_en(s.get("title") or s) for s in skills if s
                ][:10]

        # Условия
        add_info = get_en(data.get("additional_information") or "")
        if add_info:
            vacancy.offer = _extract_bullets(clean_html(add_info))

        # Зарплата
        frm = data.get("salary_from") or ""
        to = data.get("salary_to") or ""
        currency = data.get("salary_currency") or "AMD"
        if frm or to:
            vacancy.salary = f"{frm}–{to} {currency}".strip("–").strip()

        # Грейд
        level = data.get("job_candidate_level") or {}
        if isinstance(level, dict):
            vacancy.grade = get_en(level.get("title") or "")

        # Тип занятости
        job_type = data.get("job_type") or {}
        if isinstance(job_type, dict):
            vacancy.employment_type = get_en(job_type.get("title") or "")

        # Контакт
        if data.get("hr_mail"):
            vacancy.contact = data["hr_mail"]
        elif data.get("job_url"):
            vacancy.contact = data["job_url"]

    except Exception as e:
        logger.debug("Ошибка обогащения: %s", e)

    return vacancy


def _extract_bullets(html_or_text: str) -> list:
    """Извлекает пункты из HTML или текста."""
    from bs4 import BeautifulSoup
    lines = []

    # Пробуем парсить как HTML — ищем <li> теги
    soup = BeautifulSoup(html_or_text, "lxml")
    items = soup.find_all("li")
    if items:
        for li in items:
            text = li.get_text(strip=True)
            if 4 < len(text) < 300:
                lines.append(text)
            if len(lines) >= 10:
                break
        return lines

    # Если нет <li> — чистим HTML и делим по строкам
    clean = re.sub(r"<[^>]+>", "\n", html_or_text)
    clean = re.sub(r"\s+", " ", clean)
    for line in clean.split("\n"):
        line = line.strip().lstrip("•-–*▪►→✓").strip()
        if 4 < len(line) < 300:
            lines.append(line)
        if len(lines) >= 10:
            break
    return lines


def _extract_section(text: str, keywords: List[str]) -> List[str]:
    low = text.lower()
    for kw in keywords:
        idx = low.find(kw)
        if idx == -1:
            continue
        bullets = []
        for line in text[idx:idx + 1500].split("\n")[1:]:
            line = line.strip().lstrip("•-–*▪►→✓").strip()
            if not line or len(line) < 4:
                continue
            if any(k in line.lower() for k in ["responsibilities", "requirements", "we offer", "nice to have"]):
                break
            if len(line) < 300:
                bullets.append(line)
            if len(bullets) >= 10:
                break
        if bullets:
            return bullets
    return []


def _normalize_location(raw: str) -> str:
    low = raw.lower()
    if not raw:
        return "Armenia"
    if "remote" in low:
        return "Remote"
    if "hybrid" in low:
        return "Hybrid"
    if "yerevan" in low or "ереван" in low:
        return "Yerevan"
    if "armenia" in low or "армения" in low:
        return "Armenia"
    return raw.strip().title()
