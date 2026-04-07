"""
Отладка hh.ru API
Запуск: python debug_hh.py
"""
import asyncio
import aiohttp
import json

HEADERS = {
    "User-Agent": "it_armenia_vacancies_bot/1.0 (admin@it-armenia.am)",
    "Accept": "application/json",
    "HH-User-Agent": "it_armenia_vacancies_bot/1.0 (admin@it-armenia.am)",
}

ARMENIA_AREA_ID = 13  # Армения в hh.ru
IT_ROLES = ["96", "160", "10", "12", "150", "25", "36", "73", "164", "165"]


async def main():
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:

        print("=== Тест 1: все вакансии в Армении (area=13) ===")
        params = [("area", ARMENIA_AREA_ID), ("per_page", 5), ("page", 0)]
        async with session.get("https://api.hh.ru/vacancies", params=params, headers=HEADERS) as resp:
            print(f"Статус: {resp.status}")
            data = await resp.json()
            print(f"Найдено: {data.get('found', 0)}")
            for item in data.get("items", [])[:3]:
                print(f"  - {item.get('name')} | {item.get('area', {}).get('name')}")

        print()
        print("=== Тест 2: IT вакансии в Армении ===")
        params2 = (
            [("area", ARMENIA_AREA_ID), ("per_page", 5), ("page", 0)]
            + [("professional_role", r) for r in IT_ROLES]
        )
        async with session.get("https://api.hh.ru/vacancies", params=params2, headers=HEADERS) as resp:
            print(f"Статус: {resp.status}")
            data2 = await resp.json()
            print(f"Найдено: {data2.get('found', 0)}")
            for item in data2.get("items", [])[:5]:
                print(f"  - {item.get('name')} | {item.get('area', {}).get('name')}")
            if not data2.get("items"):
                print("Ответ:", json.dumps(data2, ensure_ascii=False)[:300])


asyncio.run(main())
