import json
import time
from google import genai
import asyncio

# Mantenemos tu estructura de carga de credenciales
with open("api_keys_modelos.json", 'r') as f:
    creds = json.load(f)
    api_key = creds['gemini']['api-key']

# Mantenemos el nombre de tu variable 'client'
client = genai.Client(api_key=api_key)

async def generar_storytelling(df, tema_query):
    """Envía un resumen de sentimientos a DeepSeek para obtener una conclusión."""
    if client is None or df.empty:
        return "Storytelling no disponible (falta conexión a API o datos)."

    print(f"--- Generando storytelling ---")

    resumen = df['sentimiento'].value_counts().to_dict()
    prompt = f"Analiza estos resultados de sentimiento sobre el tema '{tema_query}': {resumen}. Dame una conclusión breve, analítica y profesional sobre la opinión pública."

    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
        )

        #resultado = response.choices[0].message.content
        resultado = response.text

        #print(f"Respuesta del modelo:\n{resultado}")
        print("\n--- Storytelling generado ---")
        asyncio.sleep(2)
        return resultado
    except Exception as e:
        print(f"Error en el storytelling: {e}")
        return "La IA no pudo procesar el resumen en este momento."

async def procesar_sentimientos(data, batch_size, red_social, semaphore):
    resultados_totales = []
    resultado = ""
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        print(f"[{red_social}] Procesando batch {i//batch_size + 1} de {len(data)//batch_size + 1}...")

        async with semaphore:
            resultado_batch = await analizar_comentarios(batch, red_social)
            resultado += resultado_batch
            #resultados_totales.append(resultado_batch)

        # Pequeña pausa para evitar bloqueos por Rate Limit de la API gratuita
            await asyncio.sleep(3)
    resultados_totales = resultado.splitlines()
    return resultados_totales

async def analizar_comentarios(comentarios, red_social):
    print(f"--- [{red_social}] Analizando con gemini ---")

    prompt = (
        "Analiza la siguiente lista de comentarios extraídos de Instagram. "
        "Para cada comentario en la lista, realiza lo siguiente:\n"
        "1. Clasifica el sentimiento como 'Positivo', 'Negativo' o 'Neutro', solo con esas clases.\n"
        "2. Proporciona una explicación breve y técnica de la clasificación.\n\n"
        "Dame el resultado solo en este formato: comentario|sentimiento|explicacion\n\n"
        "No me des ningun texto adicional, solo el texto que te pido\n\n"
        f"Lista de comentarios: {comentarios}"
    )

    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt
        )

        #resultado = response.choices[0].message.content
        resultado = response.text

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

# Ejemplo de ejecución con los datos que proporcionaste
if __name__ == "__main__":
    comentarios_extraidos = [
        'vamos delci así es. vamos vamos. estás en lo correcto.',
        'cuidado por hay y yeben también...',
        'usted cuenta con su pueblo . mano de hierro...',
        'muy buena actitud delcy, ya seguro tienes un dron con tu nombre ….'
        # ... el resto de tu lista
    ]

    resultado = asyncio.run(process_instagram_gemini(comentarios_extraidos))
    print(f"Tiempo de ejecución: {resultado['duration']:.2f} segundos")
    print("\nAnálisis de Gemini:\n")
    print(resultado['result'])
