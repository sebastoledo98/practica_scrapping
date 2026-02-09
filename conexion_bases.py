import datetime
import asyncio
import uuid
from pymongo import MongoClient
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer
from qdrant_client.models import Distance, VectorParams
from motor.motor_asyncio import AsyncIOMotorClient
from utils import parse_llm_response

#qdrant_client = QdrantClient("localhost", port=6333)
qdrant_client = AsyncQdrantClient("localhost", port=6333)
embed_model = SentenceTransformer('all-MiniLM-L6-v2')

#mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_client = None
db = None
loop = None

async def conectar_mongo():
    global mongo_client, db, loop
    current_loop = asyncio.get_running_loop()
    if mongo_client is None or loop != current_loop:
        if mongo_client is not None:
            mongo_client.close()
        print("--- [MongoDB] Creando nuevo cliente para el loop actual ---")
        mongo_client = AsyncIOMotorClient("mongodb://localhost:27017/")
        db = mongo_client["proyecto_web_scraping"]
        loop = current_loop
    return db


async def initialize_qdrant():
    collection_name = "comments_sentiments"

    # Verificamos si la colección ya existe para no borrarla por error
    response = await qdrant_client.get_collections()
    collections = response.collections
    exists = any(c.name == collection_name for c in collections)

    if not exists:
        print(f"Creando colección: {collection_name}...")
        await qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=384, # Dimensión específica de all-MiniLM-L6-v2
                distance=Distance.COSINE # La métrica ideal para NLP
            ),
        )
        print("Colección creada con éxito.")
    else:
        print(f"La colección {collection_name} ya está lista.")


async def iniciar_scraping(id, tema, n_posts, n_comentarios):
    db = await conectar_mongo()
    collection = db["intentos"]
    mongo_docs = []
    document = {
        "_id": id,
        "total_posts": n_posts,
        "total_comentarios": n_comentarios,
        "tema": tema,
        "timestamp": datetime.datetime.now()
    }
    mongo_docs.append(document)

    await collection.insert_many(mongo_docs, ordered=False)


async def guardar_metricas(id, tiempo, total_comentarios, red_social, tema):
    db = await conectar_mongo()
    collection = db["metricas"]
    mongo_docs = []
    document = {
        "run_id": id,
        "tiempo": tiempo,
        "red_social": red_social,
        "total_comentarios": total_comentarios,
        "tema": tema,
        "timestamp": datetime.datetime.now()
    }
    mongo_docs.append(document)

    await collection.insert_many(mongo_docs, ordered=False)


async def guardar_comentarios(comentarios, tema, red_social):
    db = await conectar_mongo()
    collection = db["comentarios"]
    mongo_docs = []
    for comentario in comentarios:
        shared_id = str(uuid.uuid4())
        document = {
            "_id": shared_id,
            "comentario": comentario,
            "red_social": red_social.lower(),
            "tema": tema,
            "analizado": False,
            "timestamp": datetime.datetime.now()
        }
        mongo_docs.append(document)

    await collection.insert_many(mongo_docs, ordered=False)


async def guardar_posts(posts, tema, red_social):
    db = await conectar_mongo()
    collection = db["posts"]
    mongo_docs = []
    for post, comentarios in posts:
        for comentario in comentarios:
            shared_id = str(uuid.uuid4())
            document = {
                "_id": shared_id,
                "post": post,
                "comentario": comentario,
                "red_social": red_social.lower(),
                "tema": tema,
                "analizado": False,
                "timestamp": datetime.datetime.now()
            }
            mongo_docs.append(document)

    await collection.insert_many(mongo_docs, ordered=False)


async def guardar_procesados(procesados, tema, red_social):
    db = await conectar_mongo()
    await initialize_qdrant()
    collection = db["procesados"]
    #print(f"Procesados: {len(procesados)}")
    mongo_docs = []
    qdrant_data = []
    for comentario in procesados:
        try:
            texto = parse_llm_response(comentario)
            shared_id = str(uuid.uuid4())
            document = {
                "_id": shared_id,
                "comentario": texto['comentario'],
                "red_social": red_social.lower(),
                "tema": tema,
                "sentimiento": texto['sentimiento'],
                "explicacion": texto['explicacion'],
                "timestamp": datetime.datetime.now()
            }
            mongo_docs.append(document)

            vector = await asyncio.to_thread(embed_model.encode, texto['comentario'])
            qdrant_data.append(PointStruct(
                id=shared_id,
                vector=vector,
                payload={
                    "sentiment": texto['sentimiento'],
                    "network": red_social
                }
            ))
        except Exception as e:
            pass

    await collection.insert_many(mongo_docs, ordered=False)
    print(f"Insertados {len(mongo_docs)} documentos en MongoDB.")

    await qdrant_client.upsert(
        collection_name="comments_sentiments",
        points=qdrant_data
    )
    print(f"Insertados {len(qdrant_data)} documentos en Qdrant.")


async def guardar_post_procesados(posts, procesados, tema, red_social):
    db = await conectar_mongo()
    await initialize_qdrant()
    collection = db["posts_procesados"]
    #print(f"Procesados: {len(procesados)}")
    mongo_docs = []
    qdrant_data = []
    for post, texto in zip(posts, procesados):
        try:
            shared_id = str(uuid.uuid4())
            document = {
                "_id": shared_id,
                "post": post,
                "comentario": texto['comentario'],
                "red_social": red_social.lower(),
                "tema": tema,
                "sentimiento": texto['sentimiento'],
                "explicacion": texto['explicacion'],
                "timestamp": datetime.datetime.now()
            }
            mongo_docs.append(document)

            vector = await asyncio.to_thread(embed_model.encode, texto['comentario'])
            qdrant_data.append(PointStruct(
                id=shared_id,
                vector=vector,
                payload={
                    "sentiment": texto['sentimiento'],
                    "network": red_social
                }
            ))
        except Exception as e:
            pass

    await collection.insert_many(mongo_docs, ordered=False)
    print(f"Insertados {len(mongo_docs)} documentos en MongoDB.")

    await qdrant_client.upsert(
        collection_name="comments_sentiments",
        points=qdrant_data
    )
    print(f"Insertados {len(qdrant_data)} documentos en Qdrant.")


async def leer_comentarios(red_social):
    db = await conectar_mongo()
    coleccion = db['comentarios']
    cursor = coleccion.find({"red_social": red_social.lower(), "analizado": {"$ne": True}}, {"comentario": 1, "_id": 0})
    documentos = await cursor.to_list(length=None)
    return documentos


async def leer_comentarios_tema(red_social, tema):
    db = await conectar_mongo()
    coleccion = db['comentarios']
    cursor = coleccion.find({"red_social": red_social.lower(), "tema": tema, "analizado": {"$ne": True}}, {"comentario": 1, "_id": 0})
    documentos = await cursor.to_list(length=None)
    return documentos


async def leer_comentarios_post_tema(red_social, tema):
    db = await conectar_mongo()
    coleccion = db['posts']
    cursor = coleccion.find({"red_social": red_social.lower(), "tema": tema, "analizado": {"$ne": True}}, {"post": 1, "comentario": 1, "_id": 0})
    documentos = await cursor.to_list(length=None)
    return documentos


async def leer_procesados(red_social, tema):
    db = await conectar_mongo()
    coleccion = db['procesados']
    cursor = coleccion.find({"red_social": red_social.lower(), "tema": tema})
    procesados = await cursor.to_list(length=None)
    return procesados


async def leer_procesados_tema(tema):
    db = await conectar_mongo()
    coleccion = db['procesados']
    cursor = coleccion.find({"tema": tema})
    procesados = await cursor.to_list(length=None)
    return procesados


async def leer_posts_procesados_tema(tema):
    db = await conectar_mongo()
    coleccion = db['posts_procesados']
    cursor = coleccion.find({"tema": tema})
    procesados = await cursor.to_list(length=None)
    return procesados


async def buscar_tema(query, limit=10):
    db = await conectar_mongo()
    collection = db['procesados']
    consulta = asyncio.to_thread(embed_model.encode(query).tolist())
    resultados = await qdrant_client.query_points(
        collection_name="comments_sentiments",
        query=consulta,
        limit=limit
    )
    ids = [res.id for res in resultados.points]
    cursor = collection.find({"_id": {"$in": ids}})
    detalles = await cursor.to_list(length=None)
    return detalles
