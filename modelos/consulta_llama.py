from huggingface_hub import InferenceClient
import json
import asyncio

# Configuración del cliente
# Usamos DeepSeek-V3 por su alta capacidad de seguimiento de instrucciones

# Mantenemos tu estructura de carga de credenciales
with open("api_keys_modelos.json", 'r') as f:
    creds = json.load(f)
    api_key = creds['huggingface']['api-key']

client = InferenceClient(
    provider="together",
    api_key=api_key
)

async def generar_storytelling(df, tema_query):
    """Envía un resumen de sentimientos a DeepSeek para obtener una conclusión."""
    if client is None or df.empty:
        return "Storytelling no disponible (falta conexión a API o datos)."

    print(f"--- Generando storytelling ---")

    resumen = df['sentimiento'].value_counts().to_dict()
    prompt = f"Analiza estos resultados de sentimiento sobre el tema '{tema_query}': {resumen}. Dame una conclusión breve, analítica y profesional sobre la opinión pública."

    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        resultado = response.choices[0].message.content

        #print(f"Respuesta del modelo:\n{resultado}")
        print("\n--- Storytelling generado ---")
        asyncio.sleep(2)
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
            #resultados_totales.append(resultado_batch)

        # Pequeña pausa para evitar bloqueos por Rate Limit de la API gratuita
            await asyncio.sleep(3)
    resultados_totales = resultados.splitlines()
    return resultados_totales

async def analizar_comentarios(comentarios, red_social):
    print(f"--- [{red_social}] Analizando con meta-llama/Llama-3.3-70B-Instruct ---")

    prompt = (
        "Analiza la siguiente lista de comentarios extraídos de Instagram. "
        "Para cada comentario en la lista, realiza lo siguiente:\n"
        "1. Clasifica el sentimiento como 'Positivo', 'Negativo' o 'Neutro', solo con esas clases.\n"
        "2. Proporciona una explicación breve y técnica de la clasificación.\n\n"
        "Dame en solo en este formato: comentario|sentimiento|explicacion\n\n"
        "No me des ningun texto adicional ni ninguna lista, dame solo los comentarios con el analisis con el formato que te pido\n\n"
        f"Lista de comentarios: {comentarios}"
    )

    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct",
            messages=[{"role": "user", "content": prompt}],
        )

        resultado = response.choices[0].message.content

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

"""
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
resultados = analizar_comentarios(comentarios_extraidos)
print(resultados)

"""
