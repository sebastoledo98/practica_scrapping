import asyncio
import random
import os
import json
from playwright_stealth import Stealth
from playwright.async_api import async_playwright
from utils import limpiar_texto

SESSION_FILE = "session_twitter.json"
CREDENTIALS_FILE = "credenciales.json"
# Cambiar para utilizar otro navegador
# BROWSER_EXECUTABLE_PATH = '/usr/sbin/helium-browser' # O None para usar el default
BROWSER_EXECUTABLE_PATH = None

async def login_automatico(page):
    print("INICIANDO LOGIN AUTOMÁTICO...")

    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Falta el archivo {CREDENTIALS_FILE}")

    with open(CREDENTIALS_FILE, 'r') as f:
        creds = json.load(f)
        user = creds['twitter']['usuario']
        pwd = creds['twitter']['password']

    # 2. Ir al login
    await page.goto("https://x.com/i/flow/login")
    await asyncio.sleep(random.uniform(2, 4))

    # 1. Nombre de usuario
    print("Escribiendo usuario...")
    user_input = page.locator('input[autocomplete="username"]')
    await user_input.wait_for()
    for char in user:
        await user_input.type(char, delay=random.randint(50, 150))
    await page.keyboard.press("Enter")

    # 2. Contraseña (esperar a que aparezca tras el primer paso)
    print("Escribiendo contraseña...")
    pass_input = page.locator('input[name="password"]')
    await pass_input.wait_for()
    for char in pwd:
        await pass_input.type(char, delay=random.randint(50, 150))
    await page.keyboard.press("Enter")

    # Verificación de éxito (esperar al buscador o al timeline)
    try:
        await page.wait_for_selector('div[data-testid="primaryColumn"]', timeout=15000)
        print("   > Login exitoso.")
    except:
        print("   > Warning: No se detectó la interfaz principal tras el login.")

async def cargar_sesion(browser):
    if os.path.exists(SESSION_FILE):
        print(f"Detectado '{SESSION_FILE}'. Cargando sesión existente...")
        #context = await browser.new_context(storage_state=SESSION_FILE)
        context = browser
        page = await context.new_page()

        await page.goto("https://x.com/home")
        await asyncio.sleep(4)

        # Si aparece el botón de login, la sesión caducó
        if await page.locator('a[href="/login"]').is_visible():
            print("La sesión de X CADUCÓ. Reiniciando login...")
            await context.close()
            os.remove(SESSION_FILE)
            return await cargar_sesion(browser)

        return context, page
    else:
        print(f"No existe '{SESSION_FILE}'. Iniciando Login...")
        context = await browser.new_context()
        page = await context.new_page()
        await login_automatico(page)
        await context.storage_state(path=SESSION_FILE)
        return context, page

async def extraer_comentarios(page, cantidad_comentarios):
    comentarios = []
    try:
        await page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
        await asyncio.sleep(2) # Pausa para asegurar carga de comentarios
        xpath_filtro = (
            "//div[@data-testid='tweetText']"
            "//span[not(ancestor::a) and not(ancestor::button)]"
        )
        #lista_comentarios = page.locator(selector)
        lista_comentarios = page.locator(f"xpath={xpath_filtro}")

        intentos = 0
        while len(comentarios) < cantidad_comentarios and intentos < 3:
            count = await lista_comentarios.count()

            if count > 0:
                await lista_comentarios.last.scroll_into_view_if_needed()
                await page.mouse.wheel(0, 10000)
                await asyncio.sleep(random.uniform(1.5, 3))

            textos = await lista_comentarios.all_inner_texts()
            #print(f"Textos: {textos}")

            print(f"Extrayendo comentarios. Cantidad a extraer: {count}")

            textos = await lista_comentarios.all_inner_texts()

            for texto in textos:
                texto_limpio = limpiar_texto(texto.replace("\n", " ").strip())
                palabras = texto_limpio.split()
                if len(palabras) > 3:
                    #print(f"Comentario extraido: {texto_limpio}")
                    if texto_limpio not in comentarios:
                        comentarios.append(texto_limpio)

            print(f"Cantidad de comentarios extraidos: {len(comentarios)}")
            if len(comentarios) < cantidad_comentarios:
                intentos += 1
                print("Cargando mas comentarios")
    except Exception as e:
        print(f"Error {e}")

    print(f"Comentarios: {comentarios}")
    return comentarios


async def scraping(page, tema, cantidad_posts):
    print(f"BUSCANDO TEMA: '{tema}'")
    comentarios = []
    try:
# Búsqueda en tiempo real (Live) para obtener datos frescos
        search_url = f"https://x.com/search?q={tema}&src=typed_query"
        await page.goto(search_url)
        await asyncio.sleep(5)

        # Localizar enlaces de tweets (/status/)
        link_locators = page.locator('a[href*="/status/"]')

        # Extraer los atributos href de forma segura
        urls = []
        elementos_link = await link_locators.all()
        for i in range(len(elementos_link)):
            href = await elementos_link[i].get_attribute('href')
            if href and "/status/" in href:
                full_url = f"https://x.com{href}"
                if full_url not in urls:
                    urls.append(full_url)
            if len(urls) >= cantidad_posts: break

        print(f"Se encontraron {len(urls)} tweets para analizar.")

        for url in urls:
            print(f" 🐦 Procesando tweet: {url}")
            try:
                await page.goto(url)
                await asyncio.sleep(random.uniform(3, 5))
                nuevos = await extraer_comentarios(page, 50)
                comentarios.extend(nuevos)
            except Exception as e:
                print(f" Error en tweet {url}: {e}")
                continue

    except Exception as e:
        print(f"Error general en el scraper de X: {e}")
        import traceback
        traceback.print_exc()

    return comentarios


async def main():
    async with Stealth().use_async(async_playwright()) as p:
        # Configuración del navegador
        launch_args = {
            "user_data_dir": "./user_data/",
            "headless": False,
            "args": ["--disable-notifications --disable-blink-features=AutomationControlled"] # Bloquea notificaciones nativas
        }

        if BROWSER_EXECUTABLE_PATH:
            launch_args["executable_path"] = BROWSER_EXECUTABLE_PATH

        browser = await p.chromium.launch_persistent_context(**launch_args)

        # --- GESTIÓN DE SESIÓN INTELIGENTE ---
        context, page = await cargar_sesion(browser)

        # --- EJECUCIÓN DE LA TAREA ---
        await scraping(page, "venezuela", 50)

        # Finalizar
        await asyncio.sleep(2)
        await browser.close()


async def iniciar_scrapping():
    async with async_playwright() as p:
        # 'user_data' es la carpeta donde se guardará tu sesión
        context = await p.chromium.launch_persistent_context(
            './user_data',
            headless=False, # Debe ser False para loguearte manualmente la primera vez
            args=["--disable-blink-features=AutomationControlled"] # Oculta que es un bot
        )

        page = context.pages[0]
        await page.goto('https://x.com/home')

        # Si no estás logueado, el script esperará a que lo hagas manualmente
        # Una vez logueado, las siguientes veces entrará directo.
        await asyncio.sleep(60) # Tiempo para que hagas el login manual la primera vez
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
