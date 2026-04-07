"""
Ищет API endpoint staff.am.
Запуск: python find_api.py
"""
import asyncio
import aiohttp
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://staff.am/en/jobs",
}

URLS_TO_TRY = [
    "https://staff.am/api/jobs?page=1&limit=20&lang=en",
    "https://staff.am/api/jobs?page=1",
    "https://staff.am/api/v1/jobs?page=1",
    "https://staff.am/api/vacancies?page=1",
    "https://staff.am/en/api/jobs?page=1",
    "https://staff.am/graphql",
]

async def main():
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        for url in URLS_TO_TRY:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    body = await resp.text()
                    content_type = resp.headers.get("Content-Type", "")
                    print(f"\n{'='*50}")
                    print(f"URL: {url}")
                    print(f"Статус: {resp.status} | Content-Type: {content_type}")
                    print(f"Ответ: {body[:300]}")
            except Exception as e:
                print(f"\nFAIL: {url} -> {e}")

asyncio.run(main())
