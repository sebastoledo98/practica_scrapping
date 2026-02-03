from huggingface_hub import InferenceClient
import asyncio
import json

# Configuración del cliente
# Usamos DeepSeek-V3 por su alta capacidad de seguimiento de instrucciones

# Mantenemos tu estructura de carga de credenciales
with open("../api_keys_modelos.json", 'r') as f:
    creds = json.load(f)
    api_key = creds['huggingface']['api-key']

client = InferenceClient(
    provider="scaleway",
    api_key=api_key
)

async def analizar_comentarios(comentarios_extraidos):
    print("--- Analizando con deepseek ---")

    # Prompt base solicitado
    prompt_instruccion = (
        "Analiza la siguiente lista de comentarios extraídos de Instagram. "
        "Para cada comentario en la lista, realiza lo siguiente:\n"
        "1. Clasifica el sentimiento como 'Positivo', 'Negativo' o 'Neutro', solo con esas clases.\n"
        "2. Proporciona una explicación breve y técnica de la clasificación.\n\n"
        "Dame en este formato: Comentario|Sentimiento|Explicación\n\n"
    )

    # Formateamos la lista de entrada para el modelo
    cuerpo_comentarios = "\n".join([f"- {c}" for c in comentarios_extraidos])
    prompt_completo = prompt_instruccion + cuerpo_comentarios

    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
            messages=[{"role": "user", "content": prompt_completo}],
            temperature=0.2  # Mantenemos baja la temperatura para evitar alucinaciones en la explicación técnica
        )

        return response.choices[0].message.content
    except Exception as e:
        return f"Error en la API: {e}"

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
    resultados = asyncio.run(analizar_comentarios(comentarios_extraidos))
    print(resultados)
