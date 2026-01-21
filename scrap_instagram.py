import asyncio
import random
import os
import json
from playwright.async_api import async_playwright
from utils import limpiar_texto

SESSION_FILE = "session_instagram.json"
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
        user = creds['instagram']['usuario']
        pwd = creds['instagram']['password']

    # 2. Ir al login
    await page.goto("https://www.instagram.com/accounts/login/")
    await asyncio.sleep(random.uniform(2, 4))

    # 3. Llenar formulario (Humanizado)
    print("Escribiendo usuario...")
    for char in user:
        await page.locator.type(char, delay=random.randint(50, 150))
    await asyncio.sleep(random.uniform(0.5, 1.5))

    print("Escribiendo contraseña...")
    for char in pwd:
        await page.locator.type(char, delay=random.randint(50, 150))
    await asyncio.sleep(random.uniform(0.5, 1.5))

    # 4. Click en Login
    print("   > Enviando formulario...")
    btn_login = page.locator('button[type="submit"]')
    await btn_login.click()

    # 5. Esperar resultado
    # Esperamos o bien ir al Home, o bien un mensaje de error
    try:
        await page.wait_for_url("https://www.instagram.com/", timeout=15000)
        print("Login exitoso (URL Home detectada).")
    except:
        # Si falla, miramos si hay texto de error
        if await page.locator("text=La contraseña es incorrecta").is_visible():
            raise Exception("Contraseña incorrecta en el JSON.")
        print("   > Warning: No se detectó cambio de URL inmediato, verificando...")

    # 6. Manejar Pop-ups Post-Login
    # Instagram suele preguntar "Guardar información?" y "Activar notificaciones?"
    # Intentamos cerrar ambos.
    popups = ["Ahora no", "Not now", "Cancelar", "Cancel"]

    for _ in range(2): # Intentamos un par de veces por si salen secuenciales
        await asyncio.sleep(3)
        for texto in popups:
            try:
                btn = page.locator(f"button:has-text('{texto}')").first
                if await btn.is_visible():
                    print(f"   > Cerrando pop-up: '{texto}'")
                    await btn.click()
                    await asyncio.sleep(1)
            except:
                pass

async def cargar_sesion(browser):
    # CASO 1: YA EXISTE SESIÓN
    if os.path.exists(SESSION_FILE):
        print(f"Detectado '{SESSION_FILE}'. Cargando sesión existente...")
        context = await browser.new_context(storage_state=SESSION_FILE)
        page = await context.new_page()

        # Verificar que la sesión siga viva
        await page.goto("https://www.instagram.com/")
        await asyncio.sleep(3)

        # Si vemos el input de login, es que la cookie caducó
        if await page.locator('input[name="username"]').is_visible():
            print("La sesión guardada CADUCÓ. Reiniciando proceso de login...")
            await context.close()
            os.remove(SESSION_FILE) # Borramos la sesión mala
            return await cargar_sesion(browser) # Recursividad: intentamos de nuevo (irá al Caso 2)

        return context, page

    # CASO 2: NO EXISTE SESIÓN (HACER LOGIN)
    else:
        print(f"No existe '{SESSION_FILE}'. Iniciando proceso de Login...")
        context = await browser.new_context()
        page = await context.new_page()

        await login_automatico(page)

        # Guardar la cookie para el futuro
        await context.storage_state(path=SESSION_FILE)
        print(f"Sesión guardada en '{SESSION_FILE}'.")

        return context, page


async def extraer_comentarios(page, cantidad_comentarios):
    comentarios = []
    try:
        await page.wait_for_selector('main[role="main"]', timeout=15000)
        await asyncio.sleep(2) # Pausa para asegurar carga de comentarios

        xpath_filtro = (
            "//main[@role='main']//span[@dir='auto' "
            "and not(ancestor::a) "
            "and not(descendant::time) "
            "and not(ancestor::*[@role='button'])]"
        )
        #lista_comentarios = page.locator(selector)
        lista_comentarios = page.locator(f"xpath={xpath_filtro}")

        intentos = 0
        while len(comentarios) < cantidad_comentarios and intentos < 3:
            count = await lista_comentarios.count()

            if count > 0:
                await lista_comentarios.last.hover()
                await page.mouse.wheel(0, 10000)
                await asyncio.sleep(random.uniform(1.5, 3))

            textos = await lista_comentarios.all_inner_texts()
            #print(f"Textos: {textos}")

            print(f"Extrayendo comentarios. Cantidad a extraer: {count}")

            textos = await lista_comentarios.all_inner_texts()

            for i, texto in enumerate(textos):
                if i < 5:
                    continue
                texto_limpio = texto.replace("\n", " ").strip()
                texto_limpio = limpiar_texto(texto_limpio)
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
        await page.goto(f"https://www.instagram.com/explore/search/keyword/?q={tema}")
        await asyncio.sleep(5)

        link_locators = page.locator('a[href*="/p/"]').all()
        links_posts = await link_locators

        urls = []
        for i in range(min(cantidad_posts, len(links_posts))):
            href = await links_posts[i].get_attribute('href')
            urls.append(f"https://www.instagram.com{href}")

        print(f"Se encontraon {len(urls)} posts para revisar")

        for url in urls:
            print(f" Procesando post: {url}")
            try:
                await page.goto(url)
                await asyncio.sleep(random.uniform(3, 6))

                comentarios = await extraer_comentarios(page, 50)
            except Exception as e:
                print(f" Error al acceder al post {url}: {e}")
                continue
    except Exception as e:
        print(f"Error en scraping: {e}")
        # Importante para debuggear: ver dónde falló
        import traceback
        traceback.print_exc()

    return comentarios


async def iniciar_scrapping():
    async with async_playwright() as p:
        # Configuración del navegador
        launch_args = {
            "headless": False,
            "args": ["--disable-notifications"] # Bloquea notificaciones nativas
        }

        if BROWSER_EXECUTABLE_PATH:
            launch_args["executable_path"] = BROWSER_EXECUTABLE_PATH

        browser = await p.chromium.launch(**launch_args)

        # --- GESTIÓN DE SESIÓN INTELIGENTE ---
        context, page = await cargar_sesion(browser)

        # --- EJECUCIÓN DE LA TAREA ---
        await scraping(page, "venezuela", 50)

        # Finalizar
        await asyncio.sleep(2)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(iniciar_scrapping())
