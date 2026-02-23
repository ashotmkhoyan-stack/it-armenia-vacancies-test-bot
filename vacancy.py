"""
Датакласс вакансии — единая структура для всех парсеров.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Vacancy:
    title: str
    location: str                       # Remote / Yerevan / Armenia / Hybrid
    source: str                         # staff.am / hh.ru / etc.
    url: str = ""
    company: str = ""
    grade: str = ""                     # Junior / Middle / Senior / Lead
    employment_type: str = ""           # Full-time / Part-time / Contract
    working_language: str = ""          # English / Armenian / Russian
    project_context: str = ""
    responsibilities: List[str] = field(default_factory=list)
    requirements_must: List[str] = field(default_factory=list)
    requirements_nice: List[str] = field(default_factory=list)
    offer: List[str] = field(default_factory=list)
    salary: str = ""
    contact: str = ""                   # @username или ссылка
