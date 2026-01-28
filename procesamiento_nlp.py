import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from collections import Counter
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import time
import nltk
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer

# Descargamos diccionarios necesarios (solo se hace una vez)
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab')


def procesamiento_nlp(archivo_csv, red_social):
    columna_texto = 'Comentario'
    inicio_total = time.time()

    # 1. Carga de datos obtenidos de redes sociales [cite: 30]
    print(f"--- Cargando datos desde {archivo_csv} ---")
    df = None
    try:
        df = pd.read_csv(archivo_csv)
    except Exception as e:
        print(f"[{red_social}] Error al cargar el csv: {e}")
        return
    # Asegurar que no haya valores nulos en la columna de texto
    textos = df[columna_texto].astype(str).tolist()
    palabras = nltk.word_tokenize(textos)

    # PASO 3: Remover Stopwords (Palabras vacías como "el", "la", "y") [cite: 24]
    stop_words = set(stopwords.words('spanish')) # O 'english' si los perfiles son en inglés
    palabras_filtradas = [w for w in palabras if w not in stop_words]

    # PASO 4: Stemming (Cortar palabras a su raíz) [cite: 25]
    stemmer = SnowballStemmer('spanish')
    palabras_stem = [stemmer.stem(w) for w in palabras_filtradas]

    textos = " ".join(palabras_stem)


    # 2. Análisis de Sentimientos (Punto B: Otros análisis investigados) [cite: 28]
    print("--- Realizando Análisis de Sentimientos con VADER ---")
    analyzer = SentimentIntensityAnalyzer()

    # Calculamos la polaridad
    scores = [analyzer.polarity_scores(t) for t in textos]
    df['compound'] = [s['compound'] for s in scores]

    # Clasificación para la toma de decisiones [cite: 35]
    df['sentimiento'] = df['compound'].apply(
        lambda c: 'Positivo' if c >= 0.05 else ('Negativo' if c <= -0.05 else 'Neutro')
    )
    nombre_salida = f"{red_social.lower()}_procesado.csv"
    df.to_csv(nombre_salida, index=False)
    print(f" Archivo guardado: {nombre_salida}")

    # 3. Generación de Bolsa de Palabras (Punto A) [cite: 27]
    print("--- Generando Bolsa de Palabras ---")
    corpus_completo = " ".join(textos)

    # Visualización de la Nube de Palabras [cite: 32]
    wordcloud = WordCloud(
        width=800, height=400,
        background_color='white',
        colormap='viridis'
    ).generate(corpus_completo)

    # --- Visualización de Resultados ---

    # Configurar ventana de gráficos
    fig, ax = plt.subplots(1, 2, figsize=(16, 6))

    # Gráfico 1: Nube de Palabras (Bolsa de Palabras) [cite: 27]
    ax[0].imshow(wordcloud, interpolation='bilinear')
    ax[0].set_title("Bolsa de Palabras (WordCloud)", fontsize=14)
    ax[0].axis('off')

    # Gráfico 2: Distribución de Sentimientos [cite: 18, 31]
    conteo_sent = df['sentimiento'].value_counts()
    ax[1].pie(conteo_sent, labels=conteo_sent.index, autopct='%1.1f%%',
              colors=['#4CAF50', '#9E9E9E', '#F44336'], startangle=140)
    ax[1].set_title("Clasificación de Sentimientos", fontsize=14)

    plt.tight_layout()
    plt.show()

    fin_total = time.time()
    print(f"--- Proceso finalizado en {fin_total - inicio_total:.2f} segundos ---")
    return df
