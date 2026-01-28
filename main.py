import asyncio
import random
import time

# Importamos las funciones principales de cada uno de tus archivos
# Asumiendo que en cada archivo renombraste 'async def main():' por 'async def iniciar_scrapping(...):'
from scrap_instagram import iniciar_scrapping as ig_scraper
from scrap_twitter import iniciar_scrapping as tw_scraper
from scrap_facebook import iniciar_scrapping as fb_scraper
from scrap_linkedin import iniciar_scrapping as li_scraper
from procesamiento_nlp import procesamiento_nlp

async def ejecutar_con_metricas(nombre_red, funcion_scraper, tema):
    """
    Lanza el scraper de una red social con parámetros aleatorios
    y mide su desempeño individual.
    """
    # 1. Parámetros aleatorios solicitados
    #n_posts = random.randint(20, 50) + 10
    #n_comentarios = random.randint(40, 70)
    n_posts = 5
    n_comentarios = 20

    inicio_red = time.time()
    print(f"[ORQUESTADOR] Lanzando {nombre_red} -> Objetivos: {n_posts} posts, {n_comentarios} comentarios.")

    try:
        # Ejecutamos el flujo completo que ya tienes programado en cada archivo
        # Pasamos los parámetros de búsqueda y cantidad
        resultados = await funcion_scraper(tema, n_posts, n_comentarios)

        duracion = time.time() - inicio_red
        print(f"{nombre_red} finalizó. Extraídos: {len(resultados)} en {duracion:.2f}s")
        return { "red": nombre_red, "datos": resultados, "tiempo": duracion }

    except Exception as e:
        print(f"Error en la ejecución autónoma de {nombre_red}: {e}")
        return { "red": nombre_red, "datos": [], "tiempo": 0 }

async def orquestador_principal(tema_busqueda):
    print("="*60)
    print(f"INICIANDO EJECUCIÓN CONCURRENTE: TEMA '{tema_busqueda}'")
    print("="*60)

    tiempo_inicio_total = time.time()

    # Definimos la lista de tareas
    # Cada una se ejecutará de forma independiente con su propio 'async with async_playwright()'
    tareas = [
        ejecutar_con_metricas("Instagram", ig_scraper, tema_busqueda),
        ejecutar_con_metricas("Twitter", tw_scraper, tema_busqueda),
        ejecutar_con_metricas("Facebook", fb_scraper, tema_busqueda),
        ejecutar_con_metricas("LinkedIn", li_scraper, tema_busqueda),
    ]

    # asyncio.gather ejecuta los 4 flujos AL MISMO TIEMPO
    reportes = await asyncio.gather(*tareas)

    tiempo_fin_total = time.time()
    total_comentarios = sum(len(r["datos"]) for r in reportes)

    print("\n" + "—"*58)
    print(f"RESUMEN DE LA PRÁCTICA (COMPUTACIÓN PARALELA)")
    print(f"Tiempo total de orquestación: {tiempo_fin_total - tiempo_inicio_total:.2f}s")
    print("—"*60)

# Orquestador Asíncrono
async def orquestar_procesamiento():
    # Definición de las redes sociales y sus archivos correspondientes
    tareas_redes = [
        ("instagram_comentarios.csv", "Instagram"),
        ("twitter_comentarios.csv", "Twitter/X"),
        ("facebook_comentarios.csv", "Facebook"),
        ("linkedin_comentarios.csv", "LinkedIn")
    ]

    inicio_total = time.time()

    # Creamos tareas concurrentes usando to_thread para no bloquear el event loop
    tareas = [
        asyncio.to_thread(procesamiento_nlp, archivo, nombre)
        for archivo, nombre in tareas_redes
    ]

    # Ejecución concurrente
    resultados = await asyncio.gather(*tareas)

    fin_total = time.time()
    print(f"\n===== TIEMPO TOTAL CONCURRENTE: {fin_total - inicio_total:.2f}s =====") [cite: 47]


if __name__ == "__main__":
    # Tema de interés para tu Práctica 6
    TEMA = "venezuela"
    asyncio.run(orquestador_principal(TEMA))
    asyncio.run(orquestar_procesamiento())
