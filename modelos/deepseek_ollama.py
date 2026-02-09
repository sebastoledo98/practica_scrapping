import ollama
import asyncio
import pandas as pd

#with open("api_keys_modelos.json", 'r') as f:
#    creds = json.load(f)
#    api_key = creds['huggingface']['api-key']

MODELO="deepseek-r1:7b-qwen-distill-q4_K_M"


async def generar_storytelling(df, tema_query):
    """Envía un resumen de sentimientos a DeepSeek para obtener una conclusión."""
    if df.empty:
        return "Storytelling no disponible (falta conexión a API o datos)."

    print(f"--- Generando storytelling ---")

    resumen = df['sentimiento'].value_counts().to_dict()
    prompt = f"Analiza estos resultados de sentimiento sobre el tema '{tema_query}': {resumen}. Dame una conclusión breve, analítica y profesional sobre la opinión pública."

    try:
        response = await asyncio.to_thread(
            ollama.generate,
            model=MODELO,
            prompt=prompt,
            system="No saludes, no des introducciones, no generes el proceso de razonamiento, no generes listados, no generes texto extra aparte del que te piden. Genera los resultados siempre en español a menos que el usuario te pida, no combines lenguajes. Realiza una revision final del texto generado para verificar que este solo en español y sea entendible."
        )

        resultado = response['response'].strip()

        #print(f"Respuesta del modelo:\n{resultado}")
        print("\n--- Storytelling generado ---")
        await asyncio.sleep(2)
        return resultado
    except Exception as e:
        print(f"Error en el storytelling: {e}")
        return "La IA no pudo procesar el resumen en este momento."

async def procesar_sentimientos(data, batch_size, red_social, semaphore):
    resultados_totales = []
    resultados = ""
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        print(f"[{red_social}] Procesando batch {i//batch_size + 1} de {len(data)//batch_size + 1}...")

        async with semaphore:
            resultado_batch = await analizar_comentarios(batch, red_social)
            resultados += resultado_batch
            resultados_totales.append(resultado_batch)

        # Pequeña pausa para evitar bloqueos por Rate Limit de la API gratuita
            await asyncio.sleep(3)
    resultados_totales = resultados.splitlines()
    return resultados_totales

async def analizar_comentarios(comentarios, red_social):
    print(f"--- [{red_social}] Analizando con deepseek-r1:7b-qwen-distill-q4_K_M ---")

    prompt = (
        "Analiza el sentimiento de los siguientes comentarios extraidos de varias redes sociales. Devuelve el resultado exclusivamente en español.\n\n"
        "Estos son dos ejemplos de como necesito la salida\n"
        "Comentario: 'me encanta este post'\n"
        "Resultado: me encanta este post|Positivo|El usuario expresa agrado directo y entusiasmo.\n"
        "Comentario: 'no me gusta el servicio'\n"
        "Resultado: no me gusta el servicio|Negativo|El usuario manifiesta insatisfacción explícita.\n\n"
        "Procesa esta lista:\n"
        f"{comentarios}"
        "El formato de salida debe ser este: comentario|sentimiento|explicacion\n"
    )

    #prompt = (
    #    "Analiza la siguiente lista de comentarios extraídos de Instagram."
    #    "Para cada comentario en la lista, realiza lo siguiente:\n"
    #    "1. Clasifica el sentimiento como 'Positivo', 'Negativo' o 'Neutro', solo con esas clases.\n"
    #    "2. Proporciona una explicación breve y técnica de la clasificación.\n\n"
    #    "Dame en este formato: comentario|sentimiento|explicacion\n\n"
    #    "No me des ningun texto adicional, solo el texto que te pido\n\n"
    #    "Los comentarios estan en varios idiomas, pero dame el sentimiento y la explicacion solo en español\n\n"
    #    f"Lista de comentarios: {comentarios}"
    #)

    system_prompt = (
        "Actúa como un procesador de datos ciego. No razones en voz alta. "
        "Tu única función es transformar texto a formato: comentario|sentimiento|explicacion. "
        "REGLAS DE IDIOMA:\n"
        "El sentimiento DEBE ser: Positivo, Negativo o Neutro.\n"
        "El sentimiento NO DEBE ser una variacion en otro idioma\n"
        "La explicación DEBE ser en ESPAÑOL, sin importar el idioma del comentario.\n"
        "Prohibido usar inglés en la explicación.\n"
        "REGLA DE FORMATO:\n"
        "Una línea por comentario. Sin encabezados. Sin indices."
        "Solo puede ser Positivo, Negativo, Neutro, ninguna otra clase ni equivalente."
        "NO uses números ni listas (1., 2., etc.).\n"
        "NO uses etiquetas como 'Comentario:', 'Sentimiento:' o 'Explicación:'.\n"
        "CADA LÍNEA debe tener exactamente este formato: comentario|sentimiento|explicacion\n"
        "NO incluyas ninguna palabra fuera de ese formato."
    )

    #system_prompt=("No saludes, no des introducciones, no des el proceso de razonamiento, no generes listados, no generes texto extra aparte del que te piden. Trata el resultado como si fuera un csv. Genera los resultados siempre en español a menos que el usuario te pida, no combines lenguajes.")

    try:
        response = await asyncio.to_thread(
            ollama.generate,
            model=MODELO,
            prompt=prompt,
            system=system_prompt,
            options={
                'temperature': 0,
                'top_p': 0.9,
                'repeat_penalty': 1.1,
            }
        )

        resultado = response['response'].strip()

        #print(f"Respuesta del modelo:\n{resultado}")
        print("\n--- Analisis finalizado ---")
        await asyncio.sleep(2)
        return resultado

    except Exception as e:
        print(f"\n[!] Error detectado: {e}")
        if "429" in str(e):
            print("Limite de peticiones por minuto alcanzado, esperando 10 segundos")
            await asyncio.sleep(10)
        return ""


if __name__ == "__main__":
    # Tu lista de datos
    comentarios_extraidos = [
        'vamos delci así es. vamos vamos. estás en lo correcto. así es que se gobierna. jajajjajaa sigue así. . pa que venga la face 2 vamos vamos',
        'cuidado por hay y yeben también yo tengo entendido que como ya no hay presidente hay que ser elección entre tres meses me supongo yo que tienen que ser en marzo',
        'usted cuenta con su pueblo . mano de hierro como diría mi comandante chávez.. firme y digna presidenta',
        'ciertas son las palabras de delcy rodríguez venezuela es un país libre y soberano no es colonia del imperialismo',
        'muy buena actitud delcy, ya seguro tienes un dron con tu nombre ….',
        'jose manuel lindarte torres',
        'la chilindrina es la siguiente.',
        'publicación de alerta aeropuerto'
    ]

    # Ejecución
    resultados = asyncio.run(analizar_comentarios(comentarios_extraidos, "Twitter"))
    print(f"Resultado del analisis: {resultados}")

    res = resultados.splitlines()
    res = [linea for linea in res if linea.strip()]
    filas = [linea.split('|') for linea in res]
    print(f"Listado de resultados: {filas}")
    df = pd.DataFrame(filas, columns=['comentario','sentimiento','explicacion'])
    df.dropna()
    print(f"Dataframe")
    print(df.head(20))
    storytelling = asyncio.run(generar_storytelling(df, "venezuela"))
    print(f"Storytelling generado: {storytelling}")
