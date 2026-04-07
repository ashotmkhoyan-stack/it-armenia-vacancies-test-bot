"""
Запусти этот скрипт чтобы увидеть реальную структуру staff.am
и понять какие CSS-селекторы нужны.

Запуск:  python debug_staff_am.py
"""
import asyncio
import ssl
import aiohttp
from bs4 import BeautifulSoup

URL = "https://staff.am/en/jobs"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

async def main():
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(URL, headers=HEADERS) as resp:
            print(f"Статус: {resp.status}")
            html = await resp.text()

    soup = BeautifulSoup(html, "lxml")

    print("\n=== ВСЕ КЛАССЫ <div> и <li> (первые 40) ===")
    elements = soup.select("div[class], li[class], article[class]")
    classes_seen = set()
    for el in elements:
        cls = " ".join(el.get("class", []))
        if cls not in classes_seen:
            classes_seen.add(cls)
            print(f"  <{el.name} class='{cls}'>")
        if len(classes_seen) >= 40:
            break

    print("\n=== ВСЕ ССЫЛКИ содержащие 'job' или 'vacanc' ===")
    links = soup.select("a[href*='job'], a[href*='vacanc']")
    for a in links[:15]:
        print(f"  href={a.get('href')} | text={a.get_text(strip=True)[:60]}")

    print("\n=== ЗАГОЛОВКИ h2 и h3 ===")
    for h in soup.select("h2, h3")[:15]:
        print(f"  <{h.name} class='{' '.join(h.get('class',[]))}'>: {h.get_text(strip=True)[:80]}")

    print("\n=== СОХРАНЕНО: staff_am_debug.html ===")
    with open("staff_am_debug.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Открой staff_am_debug.html в браузере для просмотра.")


asyncio.run(main())
