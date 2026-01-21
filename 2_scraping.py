import asyncio
from playwright.async_api import async_playwright

async def espiar_perfil(browser, url, archivo_cookies):
    # Detectamos de qué red social es la URL
    es_facebook = "facebook.com" in url
    es_instagram = "instagram.com" in url
    
    try:
        # Cargamos las cookies correspondientes
        context = await browser.new_context(storage_state=archivo_cookies)
        
        # Bloqueamos imágenes y fuentes para que vaya MÁS RÁPIDO y gaste menos datos
        await context.route("**/*.{png,jpg,jpeg,svg,woff,woff2}", lambda route: route.abort())
        
        page = await context.new_page()
        
        print(f"[{'FB' if es_facebook else 'IG'}] Entrando a: {url}")
        await page.goto(url, timeout=60000) # Damos 60 segs por si el internet va lento
        
        # --- ESTRATEGIA DE SCROLL ---
        # Bajamos un poco para que carguen posts
        for _ in range(3): 
            await page.mouse.wheel(0, 3000)
            await asyncio.sleep(2)
        
        # --- ESTRATEGIA DE EXTRACCIÓN ---
        textos_encontrados = []
        
        if es_facebook:
            # Facebook: El texto de los posts suele estar en div[dir="auto"]
            # o dentro de elementos con role="article"
            print(f"   >>> Extrayendo posts de Facebook...")
            elementos = await page.query_selector_all('div[dir="auto"]')
            for el in elementos:
                txt = await el.inner_text()
                if len(txt) > 30: # Solo guardamos textos largos (filtramos botones o menús)
                    textos_encontrados.append(txt)
                    
        elif es_instagram:
            # Instagram: El texto suele estar en spans o h1/h2
            print(f"   >>> Extrayendo posts de Instagram...")
            # Usamos un script de navegador para sacar todo el texto visible rápido
            textos_encontrados = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('span, ul, h1')).map(el => el.innerText);
            }''')

        print(f" Terminado {url}: {len(textos_encontrados)} textos capturados.")
        await context.close()
        return textos_encontrados
        
    except Exception as e:
        print(f"❌ Error en {url}: {e}")
        return [] # Retornamos lista vacía para no romper el programa

async def principal():
    # Esta función se usa solo para pruebas individuales
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        urls = ["https://www.facebook.com/NASA/"]
        res = await espiar_perfil(browser, urls[0], "facebook_cookies.json")
        await browser.close()
        return res

if __name__ == "__main__":
    asyncio.run(principal())