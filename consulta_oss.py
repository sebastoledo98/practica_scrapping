import asyncio
import json
import os
from openai import AsyncOpenAI

with open("api_keys_modelos.json", 'r') as f:
    creds = json.load(f)
    api_key = creds['openrouter']['api-key']


# Configuración de OpenRouter
# Asegúrate de tener tu API Key en las variables de entorno o cámbiala aquí
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

async def procesar_sentimientos(data):
    print("--- Analizando con openai/gpt-oss-20b ---")

    prompt = (
        "Analiza la siguiente lista de comentarios extraídos de Instagram. "
        "Para cada comentario en la lista, realiza lo siguiente:\n"
        "1. Clasifica el sentimiento como 'Positivo', 'Negativo' o 'Neutro', solo con esas clases.\n"
        "2. Proporciona una explicación breve y técnica de la clasificación.\n\n"
        "Dame en este formato: Comentario|Sentimiento|Explicación\n\n"
        f"Lista de comentarios: {data}"
    )

    try:
        response = await client.chat.completions.create(
            model="openai/gpt-oss-20b:free",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extraemos el texto de la respuesta
        resultado = response.choices[0].message.content

        print(f"Respuesta cruda del modelo:\n{resultado}")
        print("\n--- Prueba finalizada con éxito ---")
        return resultado

    except Exception as e:
        print(f"\n[!] Error detectado: {e}")

if __name__ == "__main__":
    comentarios_extraidos = [
        'vamos delci así es. vamos vamos. estás en lo correcto.',
        'cuidado por hay y yeben también...',
        'usted cuenta con su pueblo . mano de hierro...',
        'muy buena actitud delcy, ya seguro tienes un dron con tu nombre ….'
        # ... el resto de tu lista
    ]

    asyncio.run(procesar_sentimientos(comentarios_extraidos))
