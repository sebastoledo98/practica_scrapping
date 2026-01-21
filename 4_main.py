import asyncio
import time
import matplotlib.pyplot as plt
from nltk import FreqDist # <--- Nueva importación clave para Bolsa de Palabras
from importlib import import_module
from playwright.async_api import async_playwright

scraping = import_module("2_scraping")
nlp = import_module("3_procesamiento")

async def ejecutar_practica():
    print("--- INICIO PRÁCTICA 6: BOLSA DE PALABRAS ---")
    
    # ---------------------------------------------------------
    # 1. EXTRACCIÓN (PARALELA)
    # ---------------------------------------------------------
    inicio_scraping = time.perf_counter()
    print("1. [PARALELO] Extrayendo datos de IG y FB...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Define tus objetivos aquí
        objetivos = [
            ("https://www.instagram.com/nasa/", "instagram_cookies.json"),
            ("https://www.facebook.com/NASA/", "facebook_cookies.json")
            # Agrega más si quieres
        ]
        
        tareas = [scraping.espiar_perfil(browser, url, cookie) for url, cookie in objetivos]
        resultados_listas = await asyncio.gather(*tareas)
        await browser.close()

    # Unimos todo en un solo texto gigante
    texto_crudo = " ".join([txt for lista in resultados_listas for txt in lista])
    
    fin_scraping = time.perf_counter()
    print(f"   >>> Tiempo Extracción: {fin_scraping - inicio_scraping:.4f} s")

    # ---------------------------------------------------------
    # 2. PROCESAMIENTO (NLP)
    # ---------------------------------------------------------
    inicio_nlp = time.perf_counter()
    print("2. [SECUENCIAL] Generando tokens y limpiando...")
    
    # Ahora esto nos devuelve una LISTA de palabras, no un texto
    lista_palabras = nlp.limpiar_y_procesar(texto_crudo)
    
    fin_nlp = time.perf_counter()
    print(f"   >>> Tiempo NLP: {fin_nlp - inicio_nlp:.4f} s")
    
    # ---------------------------------------------------------
    # 3. VISUALIZACIÓN: BOLSA DE PALABRAS (HISTOGRAMA)
    # ---------------------------------------------------------
    print("3. Visualizando Bolsa de Palabras (Top 20)...")
    
    if not lista_palabras:
        print("⚠️ Error: No hay palabras para graficar.")
        return

    # Calculamos la frecuencia (La verdadera "Bolsa de Palabras")
    frecuencia = FreqDist(lista_palabras)
    
    # Tomamos las 20 más comunes para que el gráfico se entienda
    mas_comunes = frecuencia.most_common(20)
    
    # Separamos palabras y cantidades para el eje X e Y
    palabras = [x[0] for x in mas_comunes]
    conteos = [x[1] for x in mas_comunes]
    
    # Generamos el gráfico de barras
    plt.figure(figsize=(12, 6))
    plt.bar(palabras, conteos, color='skyblue', edgecolor='black')
    plt.title(f"Bolsa de Palabras (Top Frecuencias)\nExtracción: {fin_scraping - inicio_scraping:.2f}s | NLP: {fin_nlp - inicio_nlp:.2f}s")
    plt.xlabel('Palabras (Stemming)')
    plt.ylabel('Frecuencia (Repeticiones)')
    plt.xticks(rotation=45, ha='right') # Rotamos las palabras para que se lean bien
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout() # Ajusta para que no se corte el texto
    plt.show()

if __name__ == "__main__":
    asyncio.run(ejecutar_practica())