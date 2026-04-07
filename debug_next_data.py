"""
Показывает структуру __NEXT_DATA__ с staff.am
Запуск: python debug_next_data.py
"""
import asyncio
import json
import re
import aiohttp

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
}

async def main():
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get("https://staff.am/en/jobs", headers=HEADERS) as resp:
            html = await resp.text()

    match = re.search(r'<script\s+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        print("❌ __NEXT_DATA__ не найден!")
        return

    data = json.loads(match.group(1))
    page_props = data.get("props", {}).get("pageProps", {})

    print("✅ __NEXT_DATA__ найден!")
    print(f"\nКлючи pageProps: {list(page_props.keys())}")

    # Показываем структуру каждого ключа
    for key, val in page_props.items():
        if isinstance(val, list):
            print(f"\n  '{key}' = список из {len(val)} элементов")
            if val and isinstance(val[0], dict):
                print(f"    Первый элемент ключи: {list(val[0].keys())}")
                print(f"    Пример: {json.dumps(val[0], ensure_ascii=False)[:300]}")
        elif isinstance(val, dict):
            print(f"\n  '{key}' = dict, ключи: {list(val.keys())}")
        else:
            print(f"\n  '{key}' = {repr(val)[:100]}")

    # Сохраняем полный JSON для изучения
    with open("next_data.json", "w", encoding="utf-8") as f:
        json.dump(page_props, f, ensure_ascii=False, indent=2)
    print("\n💾 Сохранено в next_data.json")

asyncio.run(main())
