import asyncio
import random
import os
import json
import re
from playwright.async_api import async_playwright
from utils import limpiar_texto, guardar_comentarios_csv, guardar_procesados_csv
from consulta_qwen import analizar_comentarios

# --- CONFIGURACIÓN ---
SESSION_FILE = "session_linkedin.json"
CREDENTIALS_FILE = "credenciales.json"
BROWSER_EXECUTABLE_PATH = None

async def obtener_clipboard_pegando(page):
    try:
        # 1. Inyectar un textarea invisible en el DOM
        await page.evaluate("""() => {
            const input = document.createElement('textarea');
            input.id = 'clipboard_test_area';
            input.style.position = 'fixed';
            input.style.left = '-9999px';
            document.body.appendChild(input);
            input.focus();
        }""")

        # 2. Simular el comando de pegado (Linux/Windows usa Control+V)
        # Nota: Si estuvieras en Mac sería 'Meta+V', pero usas Artix Linux.
        await page.keyboard.press("Control+V")
        await asyncio.sleep(0.5) # Espera a que el navegador procese el pegado

        # 3. Leer el valor del textarea
        contenido = await page.evaluate("document.getElementById('clipboard_test_area').value")

        # 4. Limpiar el DOM (Borrar el textarea)
        await page.evaluate("document.getElementById('clipboard_test_area').remove()")

        return contenido

    except Exception as e:
        print(f"[LinkedIn] Error al intentar pegar: {e}")
        return ""

async def escribir_humano(locator, texto):
    for char in texto:
        await locator.type(char, delay=random.randint(50, 150))

async def login_automatico(page):
    print("[LinkedIn] INICIANDO LOGIN EN LINKEDIN...")
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Falta el archivo {CREDENTIALS_FILE}")

    with open(CREDENTIALS_FILE, 'r') as f:
        creds = json.load(f)
        user = creds['linkedin']['usuario']
        pwd = creds['linkedin']['password']

    # Usamos la URL directa de login
    await page.goto("https://www.linkedin.com/login/es")
    await asyncio.sleep(random.uniform(2, 4))

    # Llenar formulario
    await escribir_humano(page.locator('#username'), user)
    await asyncio.sleep(1)
    await escribir_humano(page.locator('#password'), pwd)
    await asyncio.sleep(1)

    btn_login = page.locator('button[type="submit"]')
    await btn_login.click()

    # Verificación
    try:
        await page.wait_for_selector('#global-nav', timeout=20000)
        print("[LinkedIn] Login exitoso (Navbar detectada).")
    except:
        if await page.locator("text=Verificación").is_visible():
            print("[LinkedIn] LINKEDIN PIDIÓ CAPTCHA. Tienes 30s para resolverlo manualmente...")
            await asyncio.sleep(30)
        else:
            print("[LinkedIn] Warning: No se detectó home inmediatamente.")

async def obtener_contexto_linkedin(browser):
    if os.path.exists(SESSION_FILE):
        print(f"[LinkedIn] Detectado '{SESSION_FILE}'. Cargando sesión existente...")
        context = await browser.new_context(
            storage_state=SESSION_FILE,
            permissions=["clipboard-read", "clipboard-write"] # Vital para copiar el link
        )
        page = await context.new_page()

        await page.goto("https://www.linkedin.com/feed/", wait_until='domcontentloaded')
        await asyncio.sleep(3)

        # Si nos redirige al login o vemos el botón de "Unirse", la cookie murió
        if "login" in page.url or await page.locator('.nav__button-secondary').is_visible():
            print("[LinkedIn] La sesión de LinkedIn CADUCÓ. Reiniciando login...")
            await context.close()
            os.remove(SESSION_FILE)
            return await obtener_contexto_linkedin(browser)

        return context, page
    else:
        print(f"[LinkedIn] No existe '{SESSION_FILE}'. Iniciando Login...")
        context = await browser.new_context()
        page = await context.new_page()
        await login_automatico(page)
        # Guardamos sesión tras login exitoso
        await context.storage_state(path=SESSION_FILE)
        return context, page

async def extraer_comentarios_post(page, cantidad_objetivo):
    """Extrae comentarios entrando al detalle del post"""
    comentarios = []
    try:
        # Esperamos carga del post
        await page.wait_for_selector('div.feed-shared-update-v2', timeout=15000)
        await page.mouse.wheel(0, 2000)
        await asyncio.sleep(2)

        # XPath quirúrgico para comentarios y contenido
        xpath_filtro = (
            "//div[contains(@class, 'comments-comment-list__container')]"
            "//span[@dir='ltr' "
            "and not(ancestor::a) "
            "and not(ancestor::button) "
            "and not(ancestor::h3)]"
        )

        locator = page.locator(f"xpath={xpath_filtro}")

        # Intentar cargar más comentarios
        try:
            btn_mas = page.locator("button.comments-comments-list__load-more-comments-button")
            if await btn_mas.is_visible():
                await btn_mas.click()
                await asyncio.sleep(2)
        except:
            pass

        textos = await locator.all_inner_texts()


        for txt in textos:
            t_limpio = limpiar_texto(txt.replace("\n", " ").strip())
            if len(t_limpio.split()) > 2 and "ver traducción" not in t_limpio.lower():
                if t_limpio not in comentarios:
                    comentarios.append(t_limpio)
                    #print(f"Comentarios: {comentarios}")
            if len(comentarios) >= cantidad_objetivo: break


    except Exception as e:
        print(f"[LinkedIn] Error en post individual: {e}")

    return comentarios

async def tarea_scraping(page, tema, cantidad_posts, cantidad_comentarios):
    print(f"[LinkedIn] BUSCANDO EN LINKEDIN: '{tema}'")
    comentarios_totales = []

    try:
        # 1. Búsqueda
        url_busqueda = f"https://www.linkedin.com/search/results/content/?keywords={tema}&origin=GLOBAL_SEARCH_HEADER"
        await page.goto(url_busqueda, wait_until='domcontentloaded')

        # Esperamos al contenedor de resultados
        await page.wait_for_selector('div.search-results-container', timeout=20000)

        urls_recolectadas = set()

        # Scroll inicial
        for _ in range(3):
            await page.mouse.wheel(0, 3000)
            await asyncio.sleep(2)

        # 2. Recolección de Links vía Menú
        # Buscamos los botones de 'tres puntos'
        botones = page.locator("div.search-results-container button.feed-shared-control-menu__trigger")
        count = await botones.count()
        print(f"[LinkedIn] Analizando {count} publicaciones...")

        for i in range(count):
            #print("[LinkedIn] Siguiente post")
            if len(urls_recolectadas) >= cantidad_posts: break

            try:
                btn = botones.nth(i)
                await btn.scroll_into_view_if_needed()

                if await btn.is_visible():
                    await btn.click() # 1. Clic en los 3 puntos

                    # --- CORRECCIÓN DEL ERROR DE STRICT MODE ---
                    # El error ocurría porque hay 18 menús ocultos.
                    # 1. Usamos la clase específica del menú de posts (feed-shared-control...) para ignorar la navbar.
                    # 2. Usamos :visible para que solo seleccione el que acabamos de abrir.
                    dropdown_selector = "div.feed-shared-control-menu__content.artdeco-dropdown__content:visible"

                    dropdown = page.locator(dropdown_selector)

                    # Esperamos a que ese único menú sea estable
                    await dropdown.wait_for(timeout=3000)

                    # 2. Buscar opción "Copiar enlace" DENTRO de ese menú visible
                    # Buscamos el 'li' que contiene el texto, luego el click lo hacemos en el centro
                    opcion_copiar = dropdown.locator("li").filter(
                        has_text=re.compile(r"Copy link|Copiar enlace", re.IGNORECASE)
                    )

                    if await opcion_copiar.count() > 0:
                        # Hover para activar estilos visuales
                        await opcion_copiar.first.hover()
                        await asyncio.sleep(0.3)

                        # Click forzado
                        await opcion_copiar.first.click(force=True)

                        # --- VERIFICACIÓN CON PEGADO SIMULADO ---
                        await asyncio.sleep(1) # Espera crítica para el copiado

                        link_pegado = await obtener_clipboard_pegando(page)
                        #print(f"[LinkedIn] [Prueba Ctrl+V]: '{link_pegado}'")

                        if "linkedin.com" in link_pegado:
                            if link_pegado not in urls_recolectadas:
                                urls_recolectadas.add(link_pegado)
                                print(f"[LinkedIn] URL capturada.")
                            else:
                                print(f"[LinkedIn] Duplicada.")

                        # Cerrar menú (Vital)
                        await page.keyboard.press("Escape")
                        await asyncio.sleep(0.5)
                    else:
                        print("[LinkedIn] Opción 'Copiar' no visible en este menú.")
                        await page.keyboard.press("Escape")

            except Exception as e:
                # Si falla por timeout u otra cosa, imprimimos y cerramos menú por si acaso
                print(f"[LinkedIn] Error procesando botón: {e}")
                await page.keyboard.press("Escape")
                pass

        lista_urls = list(urls_recolectadas)
        print(f"[LinkedIn] Total posts válidos: {len(lista_urls)}")

        # 3. Visita y Extracción
        for url in lista_urls:
            print(f"[LinkedIn] Procesando: {url}")
            try:
                await page.goto(url)
                await asyncio.sleep(random.uniform(3, 5))
                nuevos = await extraer_comentarios_post(page, cantidad_comentarios)
                print(f"[LinkedIn] Comentarios extraidos del post: {len(nuevos)}")
                comentarios_totales.extend(nuevos)
            except Exception as e:
                print(f"[LinkedIn] Error navegando: {e}")

    except Exception as e:
        print(f"[LinkedIn] Error crítico LinkedIn: {e}")

    return comentarios_totales


# --- ENTRADA PARA ORQUESTADOR ---
async def iniciar_scrapping(tema, cantidad_posts, cantidad_comentarios):
    async with async_playwright() as p:
        launch_args = {"headless": False, "args": ["--disable-notifications"]}
        if BROWSER_EXECUTABLE_PATH:
            launch_args["executable_path"] = BROWSER_EXECUTABLE_PATH

        browser = await p.chromium.launch(**launch_args)
        context, page = await obtener_contexto_linkedin(browser)

        # Si no hay sesión, hacemos login (asegúrate de tener la función login_automatico completa)
        if "feed" not in page.url:
            await login_automatico(page)
            await context.storage_state(path=SESSION_FILE)

        comentarios = await tarea_scraping(page, tema, cantidad_posts, cantidad_comentarios)
        print(f"[LinkedIn] Cantidad de comentarios extraidos: {len(comentarios)}")
        #guardar_comentarios_csv(comentarios, tema, "LinkedIn")

        resultado = analizar_comentarios(comentarios)
        guardar_procesados_csv(resultado, tema, "Instagram")

        await browser.close()
        return comentarios

if __name__ == "__main__":
    asyncio.run(iniciar_scrapping("venezuela", 3, 10))
