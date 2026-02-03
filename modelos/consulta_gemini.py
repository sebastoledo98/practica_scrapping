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

async def process_instagram_gemini(data):
    print("Procesando comentarios con gemini")
    """
    Procesa la lista de comentarios extraídos usando Gemini.
    """
    start_time = time.perf_counter()

    # Preparamos el prompt para manejar la lista de textos (data)
    # Solicitamos clasificación y explicabilidad como pide la guía [cite: 17, 18]
    prompt = (
        "Analiza la siguiente lista de comentarios extraídos de Instagram. "
        "Para cada comentario en la lista, realiza lo siguiente:\n"
        "1. Clasifica el sentimiento como 'Positivo', 'Negativo' o 'Neutro', solo con esas clases.\n"
        "2. Proporciona una explicación breve y técnica de la clasificación.\n\n"
        "Dame en este formato: Comentario|Sentimiento|Explicación\n\n"
        f"Lista de comentarios: {data}"
    )

    # Mantenemos el nombre de tu variable 'response' y el modelo que usas
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt
    )

    end_time = time.perf_counter()

    print("\nAnálisis de Gemini:\n")
    #print(response.text)

    return {
        "network": "Instagram",
        "llm": "Gemini",
        "result": response.text,  # Mantenemos response.text
        "duration": end_time - start_time
    }

def procesar(lista_completa, model_id, plataforma, batch_size=20):
    """Nueva función para orquestar los 1000+ comentarios"""
    resultados_totales = []

    # Dividimos la lista en trozos de tamaño batch_size
    for i in range(0, len(lista_completa), batch_size):
        batch = lista_completa[i:i + batch_size]
        print(f"Procesando batch {i//batch_size + 1} de {len(lista_completa)//batch_size + 1}...")

        #resultado_batch = analizar_comentarios(batch, model_id, plataforma)
        #resultados_totales.append(resultado_batch)

        # Pequeña pausa para evitar bloqueos por Rate Limit de la API gratuita
        time.sleep(1)

    return "\n".join(resultados_totales)

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
