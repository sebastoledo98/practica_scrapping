import re
import csv
import time
import emoji
import pandas as pd
import matplotlib.pyplot as plt


def parse_llm_response(texto):
    print(f"Guardando respuesta del llm: {texto}")
    try:
        parts = texto.split('|')
        label = parts[1].lower().strip(" |")

        if 'posit' in label:
            label = 'Positivo'
        elif 'negat' in label:
            label = 'Negativo'
        else:
            label = 'Neutro'

        # Validamos que tengamos las 3 partes exactas
        if len(parts) == 3:
            return {
                "comentario": parts[0].strip(),
                "sentimiento": label,
                "explicacion": parts[2].strip()
            }, None
        else:
            # Si el LLM se equivocó, podemos intentar recuperar o loguear el error
            print(f"Error de formato en: {texto}")
            return None, texto
    except Exception as e:
        print(f"Error de formato en: {texto}")
        return None, texto


def limpiar_texto(texto):
    # 1. Convertir a minúsculas
    texto = texto.lower()

    # 2. Quitar URLs
    texto = re.sub(r'http\S+|www\S+|https\S+', '', texto, flags=re.MULTILINE)

    # 3. Quitar menciones (@usuario) y hashtags (#tema) para el modelo de sentimiento
    texto = re.sub(r'@\w+|#\w+', '', texto)

    # 4. Quitar emoticones
    texto = emoji.replace_emoji(texto, replace='')

    # 5. Eliminar espacios vacíos extra
    texto = re.sub(r'\s+', ' ', texto).strip()

    return texto


def guardar_procesados_csv(lista_comentarios, tema, red_social):
    inicio_guardado = time.time()
    red_social = red_social.lower()
    nombre_archivo = f"procesados/{red_social}_procesados.csv"

    print(f"[{red_social}] Guardando {len(lista_comentarios)} registros en {nombre_archivo}...")

    try:
        # Usamos utf-8-sig para que Excel en Windows reconozca las tildes correctamente
        with open(nombre_archivo, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow(['Comentario', 'Sentimiento', 'Explicación'])

            for comentario in lista_comentarios:
                writer.writerow([
                    comentario
                ])

        fin_guardado = time.time()
        print(f"[{red_social}] Se guardaron los resultados en {fin_guardado - inicio_guardado:.4f} segundos.")

    except Exception as e:
        print(f"[{red_social}] Error al escribir el CSV: {e}")


def guardar_rechazados(texto):
    with open("procesados/rechazados.txt", "w", encoding="utf-8") as archivo:
        for item in texto:
            archivo.write(f"{item}\n")

def guardar_post_comentarios_csv(posts, procesados, tema, red_social):
    ruta = f"procesados/{red_social}_post_procesados.csv"
    try:
        with open(ruta, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file, delimiter='|', quoting=csv.QUOTE_ALL)
            writer.writerow(['Red Social','Publicacion','Comentario','Sentimiento','Explicacion','Terminos'])
            red_social = red_social.lower()
            #Red Social | Publicacion | Comentario | Sentimiento | Explicacion | Terminos
            for post, procesado in zip(posts, procesados):
                writer.writerow([red_social, post, procesado['comentario'], procesado['sentimiento'], procesado['explicacion'], tema])
    except Exception as e:
        print(f"[{red_social}] Error al escribir el CSV: {e}")


def guardar_comentarios_csv(lista_comentarios, tema, red_social):
    inicio_guardado = time.time()
    red_social = red_social.lower()
    nombre_archivo = f"comentarios/{red_social}_comentarios.csv"

    print(f"[{red_social}] Guardando {len(lista_comentarios)} registros en {nombre_archivo}...")

    try:
        # Usamos utf-8-sig para que Excel en Windows reconozca las tildes correctamente
        with open(nombre_archivo, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file, delimiter=',', quoting=csv.QUOTE_ALL)
            writer.writerow(['Comentario'])

            for comentario in lista_comentarios:
                comentario = "'" + comentario + "'"
                writer.writerow([comentario])

        fin_guardado = time.time()
        print(f"[{red_social}] Proceso de guardado y limpieza finalizado en {fin_guardado - inicio_guardado:.4f} segundos.")

    except Exception as e:
        print(f"[{red_social}] Error al escribir el CSV: {e}")

def guardar_metricas(tiempo, total_comentarios, tiempo_modelo, red_social):
    red_social = red_social.lower()
    nombre_archivo = f"metricas/{red_social}_metricas.csv"

    print(f"[{red_social}] Guardando metricas en {nombre_archivo}...")

    try:
        # Usamos utf-8-sig para que Excel en Windows reconozca las tildes correctamente
        with open(nombre_archivo, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file, delimiter=',', quoting=csv.QUOTE_ALL)
            writer.writerow(['Tiempo', 'Cantidad Comentarios', 'Tiempo Analisis'])
            writer.writerow([tiempo, total_comentarios, tiempo_modelo])

        print(f"[{red_social}] Metricas guardadas.")

    except Exception as e:
        print(f"[{red_social}] Error al escribir el CSV: {e}")

def generar_graficos(red_social, archivo_datos):
    # 1. Cargar y procesar los datos
    # Nota: He procesado la cadena de texto original para convertirla en un DataFrame limpio
    df = pd.read_csv(archivo_datos)

    df.head(10)

    #df = pd.DataFrame(datos)

    # Guardar los datos limpios en un CSV
    df.to_csv('analisis_sentimientos.csv', index=False)

    # 2. Contar la frecuencia de cada sentimiento
    sentiment_counts = df['Sentimiento'].value_counts().sort_values(ascending=False)

    # 3. Generar Gráfico de Barras
    plt.figure(figsize=(10, 6))
    sentiment_counts.plot(kind='bar', color=['skyblue', 'lightgrey', 'salmon'])
    plt.title('Distribución de Sentimientos en los Comentarios')
    plt.xlabel('Sentimiento')
    plt.ylabel('Cantidad de Comentarios')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(f'grafico_barras_sentimientos_{red_social}.png')
    plt.close()

    # 4. Generar Gráfico de Pastel
    plt.figure(figsize=(8, 8))
    sentiment_counts.plot(kind='pie', autopct='%1.1f%%', startangle=140, colors=['skyblue', 'lightgrey', 'salmon'])
    plt.title('Proporción de Sentimientos')
    plt.ylabel('')
    plt.tight_layout()
    plt.savefig(f'grafico_pastel_sentimientos_{red_social}.png')
    plt.close()

