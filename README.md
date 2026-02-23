# 🤖 it_armenia_vacancies Bot

Telegram-бот, который автоматически собирает IT-вакансии, релевантные Армении,
и публикует их в канал [@it_armenia_vacancies](https://t.me/it_armenia_vacancies)
в едином стандартизированном формате.

---

## Возможности

- ✅ Парсинг **hh.ru** через официальный REST API (регион: Армения)
- ✅ Парсинг **staff.am** через HTML-скрапинг
- ✅ Фильтрация: только IT-роли + Armenia/Yerevan/Remote
- ✅ Дедупликация (по URL или по Title+Company+Location, TTL 60 дней)
- ✅ Единый формат поста по ТЗ (HTML, эмодзи, блоки)
- ✅ Защита от спам-всплесков (лимит батча + задержка между постами)
- ✅ Планировщик APScheduler (интервал настраивается)
- ✅ Очистка устаревших записей из БД

---

## Установка

```bash
# 1. Клонируй репозиторий
git clone <repo_url>
cd it_armenia_bot

# 2. Создай виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# 3. Установи зависимости
pip install -r requirements.txt

# 4. Настрой переменные окружения
cp .env.example .env
nano .env
```

---

## Настройка `.env`

| Переменная | Описание | По умолчанию |
|---|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather | **обязательно** |
| `CHANNEL_ID` | Username или ID канала | `@it_armenia_vacancies` |
| `SCRAPE_INTERVAL_MINUTES` | Интервал парсинга (мин) | `30` |
| `MAX_POSTS_PER_BATCH` | Макс. постов за один цикл | `5` |
| `DELAY_BETWEEN_POSTS` | Задержка между постами (сек) | `30` |
| `DEDUP_TTL_DAYS` | Срок хранения дедупликации (дни) | `60` |
| `LOG_LEVEL` | Уровень логов | `INFO` |

---

## Запуск

```bash
python main.py
```

### Запуск через systemd (Linux)

```ini
# /etc/systemd/system/it-armenia-bot.service

[Unit]
Description=IT Armenia Vacancies Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/it_armenia_bot
ExecStart=/opt/it_armenia_bot/.venv/bin/python main.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable it-armenia-bot
sudo systemctl start it-armenia-bot
sudo journalctl -u it-armenia-bot -f
```

---

## Структура проекта

```
it_armenia_bot/
├── main.py           # Точка входа, планировщик
├── config.py         # Конфигурация из .env
├── database.py       # SQLite, дедупликация
├── vacancy.py        # Датакласс Vacancy
├── formatter.py      # Форматирование текста поста
├── publisher.py      # Отправка в Telegram
├── scrapers/
│   ├── __init__.py
│   ├── base.py       # Базовый класс, утилиты
│   ├── hh_ru.py      # Парсер hh.ru (API)
│   └── staff_am.py   # Парсер staff.am (HTML)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Добавление нового источника

1. Создай файл `scrapers/my_source.py`
2. Унаследуй `BaseScraper` и реализуй метод `fetch_vacancies() -> List[Vacancy]`
3. Добавь парсер в `main.py` в список `scrapers`

```python
class MyScraper(BaseScraper):
    source_name = "mysite.am"

    async def fetch_vacancies(self) -> List[Vacancy]:
        # ... логика парсинга ...
        return [Vacancy(title="...", location="Yerevan", source=self.source_name)]
```

---

## Формат поста

```
<b>Senior Python Developer</b>
🏢 Acme Corp

📍 Location: Yerevan
🎯 Grade: Senior (Full-time)
🗣 Working language: English

🚀 Project context:
We are building a B2B SaaS platform for ...

🧩 Your responsibilities:
• Design and implement backend services
• ...

🧩 Requirements:
Must have:
• Python 3.10+
• PostgreSQL
Nice to have:
• Kubernetes

🎯 We offer:
• Competitive salary
• Salary: 3000–4000 USD (net)

📩 How to apply?
Apply: <ссылка>

🔗 Source: hh.ru
```

---

## Лицензия

MIT
