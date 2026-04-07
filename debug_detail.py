"""
Проверяет структуру детальной страницы вакансии staff.am
Запуск: python debug_detail.py
"""
import asyncio
import aiohttp
import json
import re

URL = "https://staff.am/en/jobs/software-development/senior-frontend-developer-72"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
}

async def main():
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(URL, headers=HEADERS) as resp:
            print(f"Статус: {resp.status}")
            html = await resp.text()

    match = re.search(
        r'<script\s+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    if not match:
        print("❌ __NEXT_DATA__ не найден!")
        return

    data = json.loads(match.group(1))
    page_props = data.get("props", {}).get("pageProps", {})

    print(f"\nКлючи pageProps: {list(page_props.keys())}")

    # Ищем объект вакансии
    for key in ["job", "vacancy", "jobDetail", "data"]:
        val = page_props.get(key)
        if val:
            print(f"\n✅ Найден ключ '{key}':")
            print(f"   Тип: {type(val)}")
            if isinstance(val, dict):
                print(f"   Ключи: {list(val.keys())}")
                # Показываем description
                desc = val.get("description") or val.get("body") or val.get("content")
                if desc:
                    print(f"   description (первые 300): {str(desc)[:300]}")
                else:
                    print("   description: НЕ НАЙДЕН")

    # Сохраняем
    with open("detail_data.json", "w", encoding="utf-8") as f:
        json.dump(page_props, f, ensure_ascii=False, indent=2)
    print("\n💾 Сохранено в detail_data.json")

asyncio.run(main())
