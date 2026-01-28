import asyncio
import time
import random
import os
import json
from playwright_stealth import Stealth
from playwright.async_api import async_playwright
from utils import limpiar_texto, guardar_comentarios_csv, guardar_procesados_csv
from consulta_deepseek import analizar_comentarios

SESSION_FILE = "session_twitter.json"
CREDENTIALS_FILE = "credenciales.json"
# Cambiar para utilizar otro navegador
# BROWSER_EXECUTABLE_PATH = '/usr/sbin/helium-browser' # O None para usar el default
BROWSER_EXECUTABLE_PATH = None

async def login_automatico(page):
    print("[Twitter] INICIANDO LOGIN AUTOMÁTICO...")

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
    print("[Twitter] Escribiendo usuario...")
    user_input = page.locator('input[autocomplete="username"]')
    await user_input.wait_for()
    for char in user:
        await user_input.type(char, delay=random.randint(50, 150))
    await page.keyboard.press("Enter")

    # 2. Contraseña (esperar a que aparezca tras el primer paso)
    print("[Twitter] Escribiendo contraseña...")
    pass_input = page.locator('input[name="password"]')
    await pass_input.wait_for()
    for char in pwd:
        await pass_input.type(char, delay=random.randint(50, 150))
    await page.keyboard.press("Enter")

    # Verificación de éxito (esperar al buscador o al timeline)
    try:
        await page.wait_for_selector('div[data-testid="primaryColumn"]', timeout=15000)
        print("[Twitter]    > Login exitoso.")
    except:
        print("[Twitter]    > Warning: No se detectó la interfaz principal tras el login.")

async def cargar_sesion(browser):
    if os.path.exists(SESSION_FILE):
        print(f"[Twitter] Detectado '{SESSION_FILE}'. Cargando sesión existente...")
        #context = await browser.new_context(storage_state=SESSION_FILE)
        context = browser
        page = await context.new_page()

        await page.goto("https://x.com/home")
        await asyncio.sleep(4)

        # Si aparece el botón de login, la sesión caducó
        if await page.locator('a[href="/login"]').is_visible():
            print("[Twitter] La sesión de X CADUCÓ. Reiniciando login...")
            await context.close()
            os.remove(SESSION_FILE)
            return await cargar_sesion(browser)

        return context, page
    else:
        print(f"[Twitter] No existe '{SESSION_FILE}'. Iniciando Login...")
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
            #print(f"[Twitter] Textos: {textos}")

            print(f"[Twitter] Extrayendo comentarios. Cantidad a extraer: {count}")

            textos = await lista_comentarios.all_inner_texts()

            for texto in textos:
                texto_limpio = limpiar_texto(texto.replace("\n", " ").strip())
                palabras = texto_limpio.split()
                if len(palabras) > 3:
                    #print(f"[Twitter] Comentario extraido: {texto_limpio}")
                    if texto_limpio not in comentarios:
                        comentarios.append(texto_limpio)

            print(f"[Twitter] Cantidad de comentarios extraidos: {len(comentarios)}")
            if len(comentarios) < cantidad_comentarios:
                intentos += 1
                print("[Twitter] Cargando mas comentarios")
    except Exception as e:
        print(f"[Twitter] Error {e}")

    #print(f"[Twitter] Comentarios: {comentarios}")
    return comentarios


async def scraping(page, tema, cantidad_posts, cantidad_comentarios):
    print(f"[Twitter] BUSCANDO TEMA: '{tema}'")
    comentarios = []
    try:
# Búsqueda en tiempo real (Live) para obtener datos frescos
        search_url = f"https://x.com/search?q={tema}&src=typed_query"
        await page.goto(search_url)
        await asyncio.sleep(5)
        urls = []
        intentos = 0
        max_intentos = 5

        while len(urls) < cantidad_posts and intentos < max_intentos:

            # Localizar enlaces de tweets (/status/)
            link_locators = page.locator('a[href*="/status/"]')

            # Extraer los atributos href de forma segura
            elementos_link = await link_locators.all()
            for elemento in elementos_link:
                href = await elemento.get_attribute('href')
                if href and "/status/" in href:
                    blacklist = ["/analytics", "/likes", "/retweets", "/likes", "/photo"]
                    if not any(word in href for word in blacklist):
                        full_url = f"https://x.com{href}"
                        if full_url not in urls:
                            urls.append(full_url)
                if len(urls) >= cantidad_posts: break

            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(random.uniform(2, 4))

            intentos += 1

        print(f"[Twitter] Se encontraron {len(urls)} tweets para analizar.")

        for url in urls:
            print(f"[Twitter] Procesando tweet: {url}")
            try:
                await page.goto(url)
                await asyncio.sleep(random.uniform(3, 5))
                nuevos = await extraer_comentarios(page, cantidad_comentarios)
                comentarios.extend(nuevos)
            except Exception as e:
                print(f"[Twitter]  Error en tweet {url}: {e}")
                continue

    except Exception as e:
        print(f"[Twitter] Error general en el scraper de X: {e}")
        import traceback
        traceback.print_exc()

    return comentarios


async def iniciar_scrapping(tema, n_posts, n_comentarios):
    async with Stealth().use_async(async_playwright()) as p:
        # Configuración del navegador
        launch_args = {
            "user_data_dir": "./user_data/",
            "headless": False,
            "args": ["--disable-notifications --disable-blink-features=AutomationControlled"] # Bloquea notificaciones nativas
        }

        if BROWSER_EXECUTABLE_PATH:
            launch_args["executable_path"] = BROWSER_EXECUTABLE_PATH

        tiempo_inicio_total = time.time()

        browser = await p.chromium.launch_persistent_context(**launch_args)

        # --- GESTIÓN DE SESIÓN INTELIGENTE ---
        context, page = await cargar_sesion(browser)

        # --- EJECUCIÓN DE LA TAREA ---
        comentarios = await scraping(page, tema, n_posts, n_comentarios)
        print(f"[Twitter] Cantidad de comentarios extraidos: {len(comentarios)}")
        #guardar_comentarios_csv(comentarios, tema, "Twitter")
        resultado = analizar_comentarios(comentarios)
        guardar_procesados_csv(resultado, tema, "Instagram")

        # Finalizar
        await asyncio.sleep(2)
        await browser.close()

        tiempo_fin_total = time.time()
        print(f"[Twitter] Tiempo total de ejecucion: {tiempo_fin_total - tiempo_inicio_total:.2f}s")

if __name__ == "__main__":
    asyncio.run(iniciar_scrapping("highguard", 53, 40))
