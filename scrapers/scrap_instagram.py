import asyncio
import time
import random
import os
import json
from playwright.async_api import async_playwright
from utils import limpiar_texto, guardar_comentarios_csv, guardar_procesados_csv, guardar_metricas
from modelos.consulta_oss import procesar_sentimientos
from conexion_bases import guardar_comentarios, guardar_posts, guardar_metricas as metricasbd

SESSION_FILE = "sesiones/session_instagram.json"
CREDENTIALS_FILE = "credenciales.json"
# Cambiar para utilizar otro navegador
# BROWSER_EXECUTABLE_PATH = '/usr/sbin/helium-browser' # O None para usar el default
BROWSER_EXECUTABLE_PATH = None


async def login_automatico(page):
    print("[Instagram] INICIANDO LOGIN AUTOMÁTICO...")

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
    print("[Instagram] Escribiendo usuario...")
    for char in user:
        await page.locator.type(char, delay=random.randint(50, 150))
    await asyncio.sleep(random.uniform(0.5, 1.5))

    print("[Instagram] Escribiendo contraseña...")
    for char in pwd:
        await page.locator.type(char, delay=random.randint(50, 150))
    await asyncio.sleep(random.uniform(0.5, 1.5))

    # 4. Click en Login
    print("[Instagram] Enviando formulario...")
    btn_login = page.locator('button[type="submit"]')
    await btn_login.click()

    # 5. Esperar resultado
    # Esperamos o bien ir al Home, o bien un mensaje de error
    try:
        await page.wait_for_url("https://www.instagram.com/", timeout=15000)
        print("[Instagram] Login exitoso (URL Home detectada).")
    except:
        # Si falla, miramos si hay texto de error
        if await page.locator("text=La contraseña es incorrecta").is_visible():
            raise Exception("Contraseña incorrecta en el JSON.")
        print("[Instagram] Warning: No se detectó cambio de URL inmediato, verificando...")

    # 6. Manejar Pop-ups Post-Login
    # Instagram suele preguntar "Guardar información?" y "Activar notificaciones?"
    # Intentamos cerrar ambos.
    popups = ["Ahora no", "Not now", "Cancelar", "Cancel"]

    for _ in range(2):  # Intentamos un par de veces por si salen secuenciales
        await asyncio.sleep(3)
        for texto in popups:
            try:
                btn = page.locator(f"button:has-text('{texto}')").first
                if await btn.is_visible():
                    print(f"[Instagram] Cerrando pop-up: '{texto}'")
                    await btn.click()
                    await asyncio.sleep(1)
            except:
                pass


async def cargar_sesion(browser):
    # CASO 1: YA EXISTE SESIÓN
    if os.path.exists(SESSION_FILE):
        print(f"[Instagram] Detectado '{SESSION_FILE}'. Cargando sesión existente...")
        context = await browser.new_context(storage_state=SESSION_FILE)
        page = await context.new_page()

        # Verificar que la sesión siga viva
        await page.goto("https://www.instagram.com/")
        await asyncio.sleep(3)

        # Si vemos el input de login, es que la cookie caducó
        if await page.locator('input[name="username"]').is_visible():
            print("[Instagram] La sesión guardada CADUCÓ. Reiniciando proceso de login...")
            await context.close()
            os.remove(SESSION_FILE)  # Borramos la sesión mala
            # Recursividad: intentamos de nuevo (irá al Caso 2)
            return await cargar_sesion(browser)

        return context, page

    # CASO 2: NO EXISTE SESIÓN (HACER LOGIN)
    else:
        print(f"[Instagram] No existe '{SESSION_FILE}'. Iniciando proceso de Login...")
        context = await browser.new_context()
        page = await context.new_page()

        await login_automatico(page)

        # Guardar la cookie para el futuro
        await context.storage_state(path=SESSION_FILE)
        print(f"[Instagram] Sesión guardada en '{SESSION_FILE}'.")

        return context, page


async def extraer_comentarios(page, cantidad_comentarios):
    comentarios = []
    try:
        await page.wait_for_selector('main[role="main"]', timeout=15000)
        await asyncio.sleep(2)  # Pausa para asegurar carga de comentarios

        xpath_filtro = (
            "//main[@role='main']//span[@dir='auto' "
            "and not(ancestor::a) "
            "and not(descendant::time) "
            "and not(ancestor::*[@role='button'])]"
        )
        # lista_comentarios = page.locator(selector)
        lista_comentarios = page.locator(f"xpath={xpath_filtro}")

        intentos = 0
        cantidad_anterior = 0
        while len(comentarios) < cantidad_comentarios and intentos < 3:
            count = await lista_comentarios.count()

            if count > 0:
                await lista_comentarios.last.hover()
                await page.mouse.wheel(0, 5000)
                await asyncio.sleep(random.uniform(1.5, 3))

            textos = await lista_comentarios.all_inner_texts()
            # print(f"[Instagram] Textos: {textos}")

            print(f"[Instagram] Extrayendo comentarios. Cantidad a extraer: {count}")

            textos = await lista_comentarios.all_inner_texts()

            if cantidad_anterior == len(textos): #no se cargaron mas comentarios
                intentos += 1
            else:
                intentos = 0

            cantidad_anterior = len(textos)

            for i, texto in enumerate(textos):
                if i < 5:
                    continue
                texto_limpio = texto.replace("\n", " ").strip()
                texto_limpio = limpiar_texto(texto_limpio)
                palabras = texto_limpio.split()
                if len(palabras) > 3:
                    if texto_limpio not in comentarios:
                        comentarios.append(texto_limpio)
                        print(f"[Instagram] Comentario extraido: {texto_limpio}")
                        if len(comentarios) >= cantidad_comentarios:
                            break

            print(f"[Instagram] Cantidad de comentarios extraidos: {len(comentarios)}")
            if len(comentarios) < cantidad_comentarios:
                print(f"[Instagram] Cargando más comentarios... ({len(comentarios)}/{cantidad_comentarios})")
    except Exception as e:
        print(f"[Instagram] Error {e}")
        print("[Instagram] No se encontraron comentarios")
        return comentarios

    #print(f"[Instagram] Comentarios: {comentarios}")
    return comentarios


async def scraping(page, tema, cantidad_posts, cantidad_comentarios):
    print(f"[Instagram] BUSCANDO TEMA: '{tema}'")
    comentarios_total = []
    max_comentarios = cantidad_posts * cantidad_comentarios
    try:
        await page.goto(f"https://www.instagram.com/explore/search/keyword/?q={tema}")
        await asyncio.sleep(5)

        #link_locators = page.locator('a[href*="/p/"]').all()
        #links_posts = await link_locators

        urls = []
        intentos = 0
        max_intentos = 10
        # MODIFICACIÓN: Mínimo requerido más 5 de margen
        objetivo_posts = cantidad_posts + 5

        while len(urls) < objetivo_posts and intentos < max_intentos:
            elementos_link = await page.locator('a[href*="/p/"]').all()

            cantidad_antes = len(urls)

            for elemento in elementos_link:
                href = await elemento.get_attribute('href')
                if href:
                    full_url = f"https://www.instagram.com{href}"
                    if full_url not in urls:
                        urls.append(full_url)
                if len(urls) >= objetivo_posts:
                    break

            if len(urls) < objetivo_posts:
                print(f"[Instagram] Buscando más posts... ({len(urls)}/{objetivo_posts})")
                await page.mouse.wheel(0, 4000)
                await asyncio.sleep(random.uniform(2, 4))

                if len(urls) == cantidad_antes:
                    intentos += 1
                else:
                    intentos = 0

        print(f"[Instagram] Se encontraron {len(urls)} posts para revisar (incluyendo margen de seguridad)")

        i = 1
        for url in urls:
            print(f"[Instagram] Procesando post: {url}, post {i}/{len(urls)}")
            try:
                i += 1
                await page.goto(url)
                await asyncio.sleep(random.uniform(3, 6))

                comentarios = await extraer_comentarios(page, cantidad_comentarios)
                post = [url, comentarios]
                comentarios_total.append(post)

                if len(comentarios) >= max_comentarios:
                    break
            except Exception as e:
                print(f"[Instagram] Error al acceder al post {url}: {e}")
                continue
    except Exception as e:
        print(f"[Instagram] Error en scraping: {e}")
        # Importante para debuggear: ver dónde falló
        import traceback
        traceback.print_exc()

    return comentarios_total


async def iniciar_scrapping(tema, n_posts, n_comentarios, id):
    async with async_playwright() as p:
        # Configuración del navegador
        launch_args = {
            "headless": False,
            # Bloquea notificaciones nativas
            "args": ["--disable-notifications"]
        }

        if BROWSER_EXECUTABLE_PATH:
            launch_args["executable_path"] = BROWSER_EXECUTABLE_PATH

        tiempo_inicio_total = time.time()

        tiempo_inicio = time.time()
        browser = await p.chromium.launch(**launch_args)

        # --- GESTIÓN DE SESIÓN INTELIGENTE ---
        context, page = await cargar_sesion(browser)

        # --- EJECUCIÓN DE LA TAREA ---
        print("--- [Instagram] Extrayendo comentarios ---")
        comentarios = await scraping(page, tema, n_posts, n_comentarios)


        tiempo_fin = time.time()
        tiempo_total_scraping = tiempo_fin - tiempo_inicio
        print(f"[Instagram] Tiempo total de ejecucion: {tiempo_total_scraping:.2f}s")
        print(f"[Instagram] Cantidad de comentarios extraidos: {len(comentarios)}")

        await asyncio.sleep(2)
        await browser.close()

        print("--- [Instagram] Guardando comentarios ---")
        #guardar_comentarios_csv(comentarios, tema, "Instagram")
        #await guardar_comentarios(comentarios, tema, "Instagram")
        await guardar_posts(comentarios, tema, "Instagram")

        #tiempo_inicio = time.time()
        #print("--- [Instagram] Analizando comentarios ---")
        #resultado = await procesar_sentimientos(comentarios, 20, "Instagram")

        #tiempo_fin = time.time()
        #tiempo_total_modelo = tiempo_fin - tiempo_inicio

        #print("--- [Instagram] Guardando analisis ---")
        #guardar_procesados_csv(resultado, tema, "Instagram")

        print("--- [Instagram] Guardando metricas ---")
        #guardar_metricas(tiempo_total_scraping, len(comentarios), tiempo_total_modelo, "Instagram")
        await metricasbd(id, tiempo_total_scraping, len(comentarios), "Instagram", tema)


if __name__ == "__main__":
    asyncio.run(iniciar_scrapping("nicolas muñoz", 50, 100))
