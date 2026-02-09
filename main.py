import asyncio
import time
import uuid

from scrapers.scrap_instagram import iniciar_scrapping as ig_scraper
from scrapers.scrap_twitter import iniciar_scrapping as tw_scraper
from scrapers.scrap_facebook import iniciar_scrapping as fb_scraper
from scrapers.scrap_linkedin import iniciar_scrapping as li_scraper

from conexion_bases import leer_comentarios_tema, guardar_procesados, iniciar_scraping, leer_comentarios_post_tema, guardar_post_procesados
from utils import guardar_post_comentarios_csv, guardar_rechazados, parse_llm_response
from modelos.deepseek_ollama import procesar_sentimientos

# Quitamos generar_graficos de aquí porque el Front (Streamlit) se encargará de eso
# from utils import generar_graficos

semaphore = asyncio.Semaphore(2)


async def analizar_comentarios_por_red(nombre_red, tema):
    print(f"Señal recibida: Iniciando análisis para {
          nombre_red} del tema {tema}...")

    # Extraemos solo los pendientes de esta red específica
    # documentos = await cursor.to_list(length=None)
    #documentos = await leer_comentarios_tema(nombre_red, tema)
    documentos = await leer_comentarios_post_tema(nombre_red, tema)
    #print(f"Documentos leidos: {documentos}")
    comentarios = [item['comentario'] for item in documentos]
    posts = [item['post'] for item in documentos]
    print(f"cantidad comentarios leidos: {len(comentarios)}")
    print(f"cantidad posts leidos: {len(posts)}")

    if not documentos:
        print(f"[IA] No se encontraron comentarios pendientes para {
              nombre_red}.")
        return

    resultado = await procesar_sentimientos(comentarios, 20, nombre_red, semaphore)
    #print(f"[{nombre_red}] Resultado del analisis: {resultado}")
    #await guardar_procesados(resultado, tema, nombre_red)
    rechazados = []
    procesar = []
    for comentario in resultado:
        procesado, rechazado = parse_llm_response(comentario)
        if rechazado is not None:
            rechazados.append(rechazado)
            continue
        procesar.append(procesado)

    #print(f"Procesados: {procesar}")
    guardar_post_comentarios_csv(posts, procesar, tema, nombre_red)
    await guardar_post_procesados(posts, procesar, tema, nombre_red)
    guardar_rechazados(rechazados)


async def ejecutar_con_metricas(nombre_red, funcion_scraper, tema, n_posts, n_comentarios, id):
    print(f"[ORQUESTADOR] Lanzando {
          nombre_red} -> Objetivos: {n_posts} posts, {n_comentarios} comentarios.")

    try:
        await funcion_scraper(tema, n_posts, n_comentarios, id)
        await analizar_comentarios_por_red(nombre_red, tema)
    except Exception as e:
        print(f"Error en la ejecución autónoma de {nombre_red}: {e}")


async def orquestador_principal(tema_busqueda, n_posts, n_comentarios):
    print("="*60)
    print(f"INICIANDO EJECUCIÓN CONCURRENTE: TEMA '{tema_busqueda}'")
    print("="*60)

    id = str(uuid.uuid4())
    await iniciar_scraping(id, tema_busqueda, n_posts, n_comentarios)

    tiempo_inicio_total = time.time()

    # Definimos la lista de tareas pasando los argumentos dinámicos
    tareas = [
        ejecutar_con_metricas("Instagram", ig_scraper, tema_busqueda, n_posts, n_comentarios, id),
        ejecutar_con_metricas("Twitter", tw_scraper, tema_busqueda, n_posts, n_comentarios, id),
        ejecutar_con_metricas("Facebook", fb_scraper, tema_busqueda, n_posts, n_comentarios, id),
        ejecutar_con_metricas("LinkedIn", li_scraper, tema_busqueda, n_posts, n_comentarios, id),
    ]

    # Ejecuta todo al mismo tiempo
    await asyncio.gather(*tareas)

    tiempo_fin_total = time.time()
    print("\n" + "—"*60)
    print(f"Tiempo total de orquestación: {
          tiempo_fin_total - tiempo_inicio_total:.2f}s")
    print("—"*60)

if __name__ == "__main__":
    # Prueba manual
    asyncio.run(orquestador_principal("cristian zamora", 2, 5))
