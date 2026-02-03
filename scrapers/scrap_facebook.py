import asyncio
import time
import re
import random
import os
import json
from playwright.async_api import async_playwright
from utils import limpiar_texto, guardar_comentarios_csv, guardar_procesados_csv, guardar_metricas
from modelos.consulta_oss import procesar_sentimientos

SESSION_FILE = "sesiones/session_facebook.json"
CREDENTIALS_FILE = "credenciales.json"
BROWSER_EXECUTABLE_PATH = None

async def login_automatico(page):
    print("[Facebook] INICIANDO LOGIN AUTOMÁTICO EN FACEBOOK...")

    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Falta el archivo {CREDENTIALS_FILE}")

    with open(CREDENTIALS_FILE, 'r') as f:
        creds = json.load(f)
        user = creds['facebook']['usuario']
        pwd = creds['facebook']['password']

    await page.goto("https://m.facebook.com/")
    await asyncio.sleep(random.uniform(2, 4))

    # Manejar banner de cookies (común en Europa/ciertas regiones)
    try:
        btn_cookies = page.locator('button[data-cookiebanner="accept_button"]')
        if await btn_cookies.is_visible():
            await btn_cookies.click()
    except:
        pass

    print("[Facebook] Escribiendo usuario...")
    await page.fill("#email", user)
    await asyncio.sleep(random.uniform(0.5, 1.5))

    print("[Facebook] Escribiendo contraseña...")
    await page.fill("#pass", pwd)
    await asyncio.sleep(random.uniform(0.5, 1.5))

    print("[Facebook] > Enviando formulario...")
    await page.click('button[name="login"]')

    try:
        # Esperar a que cargue el feed principal
        await page.wait_for_selector('div[role="feed"]', timeout=15000)
        print("[Facebook] Login exitoso.")
    except:
        print("[Facebook] Warning: No se detectó el feed, verifica si hay 2FA o error de credenciales.")

async def cargar_sesion(browser, device_settings):
    if os.path.exists(SESSION_FILE):
        print(f"[Facebook] Cargando sesión de Facebook...")
        context = await browser.new_context(storage_state=SESSION_FILE, **device_settings)
        page = await context.new_page()

        #await page.goto("https://www.facebook.com/")
        await page.goto("https://m.facebook.com/")
        await asyncio.sleep(4)

        # Si aparece el ID de login, la sesión expiró
        if await page.locator('#email').is_visible():
            print("[Facebook] Sesión caducada. Re-autenticando...")
            await context.close()
            os.remove(SESSION_FILE)
            return await cargar_sesion(browser)
        return context, page
    else:
        context = await browser.new_context(**device_settings)
        page = await context.new_page()
        await login_automatico(page)
        await context.storage_state(path=SESSION_FILE)
        return context, page

async def extraer_comentarios(page, cantidad_comentarios):
    comentarios = []
    # Expresión regular para limpiar caracteres raros de Facebook (PUA)
    regex_raros = re.compile(r'[\uE000-\uF8FF]|\U000F0000-\U000FFFFF|\U00100000-\U0010FFFFF')

    # Palabras que indican que los comentarios aún no han empezado
    marcadores_inicio = ["más pertinentes", "todos los comentarios", "comentarios"]

    try:
        xpath_comentarios = "//div[@dir='auto']"
        intentos = 0
        han_empezado_comentarios = False

        while len(comentarios) < cantidad_comentarios and intentos < 5:
            await page.mouse.wheel(0, 1500)
            await asyncio.sleep(2)

            elementos = page.locator(xpath_comentarios)
            count = await elementos.count()

            for i in range(count):
                raw_texto = await elementos.nth(i).inner_text()

                # 1. Limpiar caracteres raros y espacios
                texto_limpio = regex_raros.sub('', raw_texto).strip()
                texto_limpio = limpiar_texto(texto_limpio.replace("\n", " "))

                #print(f"Texto limpio {texto_limpio}")

                if not texto_limpio:
                    continue

                # 2. Detectar el inicio real de los comentarios
                # Si encontramos "Más pertinentes", lo que sigue son nombres y comentarios
                if not han_empezado_comentarios:
                    if any(m in texto_limpio.lower() for m in marcadores_inicio):
                        han_empezado_comentarios = True
                    continue # Seguimos saltando hasta encontrar el marcador

                # 3. Filtrar metadatos de los comentarios (Nombres, Horas, Botones)
                # Un comentario real suele ser largo. Los nombres suelen ser cortos o estar solos.
                # También filtramos el texto de "respuestas anteriores"
                texto_lower = texto_limpio.lower()
                es_basura = any(x in texto_lower for x in [
                    "responder", "compartir",
                    "ver respuestas", "más pertinentes", "autor", "ver las",
                    "..."
                ])

                if han_empezado_comentarios and not es_basura:
                    # Validamos longitud para evitar que el nombre del usuario se guarde como comentario
                    if len(texto_limpio.split()) > 3 and texto_limpio not in comentarios:
                        comentarios.append(texto_limpio)

                if len(comentarios) >= cantidad_comentarios: break

            intentos += 1

    except Exception as e:
        print(f"[Facebook] Error extrayendo: {e}")

    return comentarios

async def scraping(page, tema, cantidad_posts, cantidad_comentarios):
    print(f"[Facebook] Buscando: '{tema}'")
    comentarios_totales = []
    ids_procesados = set()

    #search_url = f"https://m.facebook.com/search/posts/?q={tema}"
    search_url = f"https://m.facebook.com/search_results/?q={tema}"
    await page.goto(search_url)
    await asyncio.sleep(5)

    while len(ids_procesados) < cantidad_posts:
        # Localizar los contenedores que identificaste
        contenedores = await page.locator('div[data-tracking-duration-id]').all()

        for post in contenedores:
            if len(ids_procesados) >= cantidad_posts: break

            post_id = await post.get_attribute("data-tracking-duration-id")
            if post_id in ids_procesados: continue

            try:
                # Buscar el disparador que mencionaste: "Toca para ver los comentarios..."
                trigger = post.locator('div[aria-label*="ver los comentarios"]')

                if await trigger.is_visible():
                    print(f"[Facebook] Abriendo post ID: {post_id}")
                    await trigger.click()
                    await asyncio.sleep(3) # Esperar carga del post

                    # Extraer comentarios usando tu función
                    coms = await extraer_comentarios(page, cantidad_comentarios)
                    print(f"Comentarios extraidos: {coms}")
                    comentarios_totales.extend(coms)

                    ids_procesados.add(post_id)

                    # Volver a la lista de búsqueda
                    await page.go_back()
                    await asyncio.sleep(3)

                    # Re-localizar los contenedores tras volver (importante por el cambio de DOM)
                    break
            except Exception as e:
                print(f"[Facebook] Error en post {post_id}: {e}")

        # Scroll en la lista de búsqueda si necesitamos más posts
        await page.mouse.wheel(0, 1500)
        await asyncio.sleep(2)

    return comentarios_totales

async def iniciar_scrapping(tema, n_posts, n_comentarios):
    async with async_playwright() as p:
        # Configuramos la emulación móvil
        device = p.devices['Pixel 7']

        launch_args = {"headless": False, "args": ["--disable-notifications"]}

        tiempo_inicio = time.time()
        browser = await p.chromium.launch(**launch_args)

        # Creamos el contexto emulando el móvil
        context = await browser.new_context(**device)

        # Aquí cargarías tu sesión/cookies si ya las tienes
        context, page = await cargar_sesion(browser, device)

        comentarios = await scraping(page, tema, n_posts, n_comentarios)

        tiempo_fin = time.time()
        tiempo_total_scraping = tiempo_fin - tiempo_inicio

        print(f"[Facebook] Cantidad de comentarios extraidos: {len(comentarios)}")
        print(f"[Facebook] Tiempo total de ejecucion: {tiempo_total_scraping:.2f}s")

        await asyncio.sleep(2)
        await browser.close()

        guardar_comentarios_csv(comentarios, tema, "Facebook")

        tiempo_inicio = time.time()
        resultado = await procesar_sentimientos(comentarios, 20, "Facebook")
        tiempo_fin = time.time()
        tiempo_total_modelo = tiempo_fin - tiempo_inicio

        guardar_procesados_csv(resultado, tema, "Facebook")
        guardar_metricas(tiempo_total_scraping, len(comentarios), tiempo_total_modelo, "Facebook")


if __name__ == "__main__":
    asyncio.run(iniciar_scrapping("nicolas muñoz", 50, 100))
