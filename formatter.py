"""
Форматирует вакансию в текст для Telegram-канала по стандарту ТЗ.
"""
from vacancy import Vacancy


def format_vacancy(v: Vacancy) -> str:
    """
    Возвращает готовый текст поста по шаблону ТЗ.
    Блоки с пустыми данными пропускаются.
    Поля на русском языке не выводятся.
    """
    # Очищаем русскоязычные поля
    v.project_context = clean_field(v.project_context)
    v.responsibilities = clean_list(v.responsibilities)
    v.requirements_must = clean_list(v.requirements_must)
    v.requirements_nice = clean_list(v.requirements_nice)
    v.offer = clean_list(v.offer)
    v.salary = clean_field(v.salary)
    v.company = clean_field(v.company)

    lines: list[str] = []

    # --- Заголовок ---
    lines.append(f"<b>{_esc(v.title)}</b>")
    if v.company:
        lines.append(f"🏢 {_esc(v.company)}")
    lines.append("")

    # --- Локация ---
    lines.append(f"📍 Location: {_esc(v.location)}")

    # --- Грейд + тип занятости ---
    grade_line = ""
    if v.grade and v.employment_type:
        grade_line = f"🎯 Grade: {_esc(v.grade)} ({_esc(v.employment_type)})"
    elif v.grade:
        grade_line = f"🎯 Grade: {_esc(v.grade)}"
    elif v.employment_type:
        grade_line = f"🎯 Employment: {_esc(v.employment_type)}"
    if grade_line:
        lines.append(grade_line)

    # --- Язык работы ---
    if v.working_language:
        lines.append(f"🗣 Working language: {_esc(v.working_language)}")

    lines.append("")

    # --- Контекст проекта ---
    if v.project_context:
        lines.append("🚀 Project context:")
        lines.append(_esc(v.project_context))
        lines.append("")

    # --- Обязанности ---
    if v.responsibilities:
        lines.append("🧩 <b>Your responsibilities:</b>")
        for item in v.responsibilities:
            lines.append(f"• {_esc(item)}")
        lines.append("")

    # --- Требования ---
    if v.requirements_must or v.requirements_nice:
        lines.append("🧩 <b>Requirements:</b>")
        if v.requirements_must:
            lines.append("Must have:")
            for item in v.requirements_must:
                lines.append(f"• {_esc(item)}")
        if v.requirements_nice:
            lines.append("Nice to have:")
            for item in v.requirements_nice:
                lines.append(f"• {_esc(item)}")
        lines.append("")

    # --- Оффер ---
    if v.offer or v.salary:
        lines.append("🎯 <b>We offer:</b>")
        for item in v.offer:
            lines.append(f"• {_esc(item)}")
        if v.salary:
            lines.append(f"• Salary: {_esc(v.salary)}")
        lines.append("")

    # --- Как откликнуться ---
    if v.contact or v.url:
        lines.append("📩 <b>How to apply?</b>")
        if v.contact:
            lines.append(f"Contact: {_esc(v.contact)}")
        if v.url:
            lines.append(f'Apply: <a href="{v.url}">open vacancy</a>')
        lines.append("")

    # --- Источник ---
    lines.append(f"🔗 Source: {_esc(v.source)}")

    # Убираем лишние пустые строки в конце
    text = "\n".join(lines).rstrip()
    return text


def _esc(text: str) -> str:
    """Экранирует HTML-спецсимволы для parse_mode=HTML."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def is_russian_text(text: str) -> bool:
    """Проверяет, содержит ли текст преимущественно кириллицу или армянский."""
    if not text:
        return False
    non_latin = sum(1 for c in text if '\u0400' <= c <= '\u04FF' or '\u0530' <= c <= '\u058F')
    total = sum(1 for c in text if c.isalpha())
    return total > 0 and (non_latin / total) > 0.3


def clean_field(text: str) -> str:
    """Возвращает текст только если он не на русском."""
    return "" if is_russian_text(text) else text


def clean_list(items: list) -> list:
    """Фильтрует русскоязычные пункты из списка."""
    return [i for i in items if not is_russian_text(i)]
