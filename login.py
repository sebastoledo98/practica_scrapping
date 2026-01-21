import asyncio
from playwright.async_api import async_playwright

async def guardar_cookies():
    async with async_playwright() as p:
        # Abrimos el navegador con "cabeza" (visible)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Vamos a Instagram (o la red que elijas)
        await page.goto("https://www.instagram.com/")
        
        print("ACCIÓN REQUERIDA: Por favor, inicia sesión manualmente en la ventana del navegador.")
        input("Cuando hayas entrado a tu perfil, presiona ENTER aquí en la consola...")

        # Guardamos tu sesión en un archivo
        await context.storage_state(path="instagram_cookies.json")
        print("¡Cookies guardadas! Ya puedes cerrar el navegador.")
        await browser.close()

asyncio.run(guardar_cookies())