import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer

# Aseguramos descargas necesarias
nltk.download('punkt')
nltk.download('stopwords')

def limpiar_y_procesar(texto_crudo):
    print("--- Iniciando Procesamiento NLP ---")
    
    # 1. Limpieza general
    texto = texto_crudo.lower()
    # Eliminamos URLs, menciones (@) y hashtags (#)
    texto = re.sub(r'http\S+|www\S+|https\S+', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'\@\w+|\#', '', texto) 
    texto = re.sub(r'[^\w\s]', '', texto) # Eliminamos puntuación
    
    # 2. Tokenización (Partir en lista)
    palabras = nltk.word_tokenize(texto)
    
    # 3. Stopwords
    stop_words = set(stopwords.words('spanish'))
    # Agregamos stopwords comunes en redes que no aportan nada
    stop_words.update(["si", "mas", "q", "k", "com", "posts", "likes", "reply", "view", "share"]) 
    
    palabras_filtradas = [w for w in palabras if w not in stop_words and len(w) > 2]
    
    # 4. Stemming (Opcional: A veces confunde la gráfica, si quieres palabras exactas comenta esto)
    stemmer = SnowballStemmer('spanish')
    palabras_stem = [stemmer.stem(w) for w in palabras_filtradas]
    
    # RETORNAMOS LA LISTA (NO EL STRING) PARA PODER CONTARLAS
    return palabras_stem