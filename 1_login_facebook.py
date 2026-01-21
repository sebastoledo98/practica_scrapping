import asyncio
from playwright.async_api import async_playwright

async def guardar_cookies_fb():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("--- Abriendo Facebook ---")
        await page.goto("https://www.facebook.com/")
        
        print("🔴 ACCIÓN REQUERIDA: Logueate manualmente.")
        print("NOTA: Si sale un popup de cookies, acéptalo.")
        input("🟢 Cuando veas tu muro de noticias, presiona ENTER aquí...")

        # Guardamos la llave
        await context.storage_state(path="facebook_cookies.json")
        print("¡Cookies de Facebook guardadas!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(guardar_cookies_fb())