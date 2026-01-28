import re
import os
from datetime import datetime
import csv
import time
import emoji

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
    nombre_archivo = f"{red_social}_procesados.csv"

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


def guardar_comentarios_csv(lista_comentarios, tema, red_social):
    inicio_guardado = time.time()
    red_social = red_social.lower()
    nombre_archivo = f"{red_social}_comentarios.csv"

    print(f"[{red_social}] Guardando {len(lista_comentarios)} registros en {nombre_archivo}...")

    try:
        # Usamos utf-8-sig para que Excel en Windows reconozca las tildes correctamente
        with open(nombre_archivo, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow(['Comentario'])

            writer.writerow([
                lista_comentarios
            ])

        fin_guardado = time.time()
        print(f"[{red_social}] Proceso de guardado y limpieza finalizado en {fin_guardado - inicio_guardado:.4f} segundos.")

    except Exception as e:
        print(f"[{red_social}] Error al escribir el CSV: {e}")
