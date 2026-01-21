import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer

# Descargamos diccionarios necesarios (solo se hace una vez)
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab')

def limpiar_y_procesar(texto_crudo):
    print("--- Iniciando Procesamiento NLP ---")

    # PASO 1: Limpieza (Minúsculas y quitar basura) [cite: 21]
    texto = texto_crudo.lower()
    texto = re.sub(r'http\S+|www\S+|https\S+', '', texto, flags=re.MULTILINE) # Adiós URLs
    texto = re.sub(r'[^\w\s]', '', texto) # Adiós signos de puntuación

    # PASO 2: Tokenización (Partir en palabras) [cite: 22]
    palabras = nltk.word_tokenize(texto)

    # PASO 3: Remover Stopwords (Palabras vacías como "el", "la", "y") [cite: 24]
    stop_words = set(stopwords.words('spanish')) # O 'english' si los perfiles son en inglés
    palabras_filtradas = [w for w in palabras if w not in stop_words]

    # PASO 4: Stemming (Cortar palabras a su raíz) [cite: 25]
    stemmer = SnowballStemmer('spanish')
    palabras_stem = [stemmer.stem(w) for w in palabras_filtradas]

    texto_final = " ".join(palabras_stem)
    return texto_final

