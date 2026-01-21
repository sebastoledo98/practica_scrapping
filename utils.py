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

def guardar_comentarios_csv(lista_comentarios, tema, red_social):
    """
    Guarda los datos en un CSV y mide el tiempo del proceso.
    """
    inicio_guardado = time.time()
    nombre_archivo = f"dataset_{tema.replace(' ', '_')}.csv"

    # Definimos si el archivo es nuevo para escribir la cabecera
    file_exists = os.path.isfile(nombre_archivo)

    print(f"💾 Guardando {len(lista_comentarios)} registros en {nombre_archivo}...")

    try:
        # Usamos utf-8-sig para que Excel en Windows reconozca las tildes correctamente
        with open(nombre_archivo, mode='a', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)

            # Cabecera (solo si el archivo es nuevo)
            if not file_exists:
                writer.writerow(['Fecha_Extraccion', 'Red_Social', 'Tema', 'Texto_Original', 'Texto_Limpio'])

            for comentario in lista_comentarios:

                # Solo guardamos si el texto limpio no quedó vacío tras el proceso
                if len(comentario) > 2:
                    writer.writerow([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        red_social,
                        tema,
                        comentario,
                    ])

        fin_guardado = time.time()
        print(f"✅ Proceso de guardado y limpieza finalizado en {fin_guardado - inicio_guardado:.4f} segundos.")

    except Exception as e:
        print(f"❌ Error al escribir el CSV: {e}")
