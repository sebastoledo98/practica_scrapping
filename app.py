import sys
import asyncio
import time
import streamlit as st
import pandas as pd
import plotly.express as px
from conexion_bases import leer_procesados_tema, leer_posts_procesados_tema
from modelos.consulta_oss import generar_storytelling

# --- FIX PARA WINDOWS ---
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# --- IMPORTACIÓN DEL BACKEND ---
from main import orquestador_principal

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Dashboard Social Analytics",
                   layout="wide", page_icon="")

st.title("Análisis de Opinión Pública - Práctica Paralela")
st.markdown(
    "Extracción concurrente y análisis de sentimientos con **GTP-OSS** y **MongoDB**.")

# --- SIDEBAR ---
st.sidebar.header("⚙️ Parámetros de Control")
tema = st.sidebar.text_input(
    "Tema a investigar (Query)", value="Elecciones 2025")
n_posts = st.sidebar.slider("Posts por red social", 1, 50, 3)
n_comentarios = st.sidebar.slider("Comentarios por post", 5, 200, 10)
btn_scraping = st.sidebar.button("Iniciar Análisis Concurrente")
btn_consulta = st.sidebar.button("Realizar consulta en la base")


def cargar_datos_mongo(query_tema):
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        # cursor = coleccion.find({"tema": query_tema})
        # df = pd.DataFrame(list(cursor))
        #procesados = loop.run_until_complete(leer_procesados_tema(query_tema))
        procesados = loop.run_until_complete(leer_posts_procesados_tema(query_tema))
        #procesados = leer_procesados_tema(query_tema)
        df = pd.DataFrame(procesados)

        if not df.empty and '_id' in df.columns:
            # Eliminamos el ID de Mongo para el DataFrame
            df = df.drop(columns=['_id'])
        return df
    except Exception as e:
        st.error(f"Error de conexión con MongoDB: {e}")
        print(f"Error de conexión con MongoDB: {e}")
        return pd.DataFrame()


def scraping(tema):
    status = st.status(f"Procesando: {tema}...", expanded=True)
    try:
        status.write("Lanzando spiders concurrentes (Playwright)...")
        # El orquestador debe encargarse de guardar en la colección 'procesados'
        asyncio.run(orquestador_principal(tema, n_posts, n_comentarios))

        status.update(label="Análisis finalizado",
                      state="complete", expanded=False)
        st.success(f"Datos almacenados en MongoDB (Colección: comentarios)")
        time.sleep(1)  # Pausa para sincronización
    except Exception as e:
        status.update(label="Error en la ejecución", state="error")
        st.error(f"Se produjo un error en el backend: {e}")

# --- SECCIÓN DE VISUALIZACIÓN ---


def consulta_base(tema):
    df_global = cargar_datos_mongo(tema)

    if not df_global.empty:
        # 1. KPIs Globales
        st.divider()
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Comentarios", len(df_global))
        kpi2.metric("Sentimiento Dominante",
                    df_global['sentimiento'].mode()[0])
        kpi3.metric("Fuentes Activas", df_global['red_social'].nunique())

        # 2. Gráficos de Análisis
        c1, c2 = st.columns(2)
        colores_map = {'Positivo': '#2ecc71',
                       'Negativo': '#e74c3c', 'Neutro': '#95a5a6'}

        with c1:
            st.subheader("Distribución Global de Sentimiento")
            fig = px.pie(df_global, names='sentimiento', color='sentimiento',
                         color_discrete_map=colores_map, hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.subheader("Sentimiento por Red Social")
            df_bar = df_global.groupby(
                ['red_social', 'sentimiento']).size().reset_index(name='Conteo')
            fig2 = px.bar(df_bar, x='red_social', y='Conteo', color='sentimiento', barmode='group',
                          color_discrete_map=colores_map)
            st.plotly_chart(fig2, use_container_width=True)

        # 3. Storytelling generado por DeepSeek
        storytelling = asyncio.run(generar_storytelling(df_global, tema))
        #storytelling = "La IA no pudo generar el storytelling"
        st.info(f"**Interpretación de la IA:** {storytelling}")

        # 4. Explorador Detallado por Red Social
        st.divider()
        st.subheader("🔍 Desglose por Fuente")

        redes_presentes = sorted(df_global['red_social'].unique())
        tabs = st.tabs(redes_presentes)

        for i, red in enumerate(redes_presentes):
            with tabs[i]:
                df_red = df_global[df_global['red_social'] == red]

                # Sub-métricas por red
                m1, m2 = st.columns(2)
                conteo_red = len(df_red)
                dominante_red = df_red['sentimiento'].mode()[0]
                m1.write(f"**Total en {red}:** {conteo_red}")
                m2.write(f"**Tendencia en {red}:** {dominante_red}")

                # Tabla de datos
                st.dataframe(
                    df_red[['comentario', 'sentimiento',
                            'explicacion', 'timestamp']],
                    use_container_width=True,
                    hide_index=True
                )

    else:
        if not btn_scraping:
            st.info(
                f"Escribe un tema en la barra lateral y presiona 'Iniciar Análisis' para consultar la base de datos.")
        else:
            st.warning(f"No se encontraron registros para el tema '{
                       tema}' en MongoDB. Revisa que el backend esté insertando datos correctamente.")


# --- FLUJO DE EJECUCIÓN ---
if btn_scraping:
    scraping(tema)
    consulta_base(tema)

if btn_consulta:
    consulta_base(tema)

# Pie de página
st.sidebar.markdown("---")
st.sidebar.caption("Proyecto de Computación Paralela - 2026")
