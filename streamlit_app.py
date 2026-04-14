import streamlit as st
import pandas as pd
import easyocr
import cv2
import numpy as np
from PIL import Image, ImageOps
from datetime import datetime
import re
import urllib.parse
import json
import io
from openai import OpenAI

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="TropiExpress v13.0 (IA Total)", page_icon="🛒", layout="wide")

# Inicializar estados si no existen
if 'base_datos' not in st.session_state:
    st.session_state.base_datos = []
if 'temp_datos' not in st.session_state:
    st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}
if 'dictado_input' not in st.session_state:
    st.session_state.dictado_input = ""

# --- CONEXIÓN IA ---
try:
    client = OpenAI(
        api_key=st.secrets["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com"
    )
except Exception as e:
    st.error(f"Error de llave/configuración: {e}")
    client = None

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False)

reader = load_ocr()

# --- FUNCIÓN MAESTRA ---
def procesar_con_ia(texto_crudo):
    if not client:
        st.error("Error: Cliente IA no configurado.")
        return

    # Limpiamos el texto de posibles saltos de línea raros
    texto_limpio_entrada = texto_crudo.replace('\n', ' ').strip()

    prompt = f"""
    Extrae datos de este pedido en Medellín: "{texto_limpio_entrada}"
    Responde ÚNICAMENTE un JSON con: "nombre", "telefono" (10 dígitos), "direccion" (MAYÚSCULAS).
    Si falta el nombre, pon "CLIENTE NUEVO".
    """

    with st.spinner("IA procesando..."):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Eres un extractor de datos JSON preciso."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            res_texto = response.choices[0].message.content.strip()
            # Limpiar posibles bloques de código de la IA
            res_texto = re.sub(r'```json\s*|```', '', res_texto)
            json_data = json.loads(res_texto)
            
            # Actualizar estado
            st.session_state.temp_datos['n'] = json_data.get('nombre', 'CLIENTE NUEVO')
            st.session_state.temp_datos['t'] = str(json_data.get('telefono', ''))
            st.session_state.temp_datos['d'] = json_data.get('direccion', '')
            st.toast("¡Datos extraídos con éxito!", icon="✅")

        except Exception as e:
            st.error(f"Error de procesamiento: {e}")

# --- COMPRESIÓN IMAGEN ---
def comprimir_imagen(archivo):
    img = Image.open(archivo)
    img = ImageOps.exif_transpose(img)
    img.thumbnail((800, 800))
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="JPEG", quality=75)
    buffer.seek(0)
    return Image.open(buffer)

# --- INTERFAZ ---
st.title("🛒 TropiExpress v13.0")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📥 Entrada de Datos")
    tab1, tab2 = st.tabs(["📸 Foto", "🎙️ Dictado"])
    
    with tab1:
        foto = st.file_uploader("Subir nota", type=['jpg', 'jpeg', 'png'])
        if foto and st.button("Analizar Foto", use_container_width=True):
            img = comprimir_imagen(foto)
            gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
            texto_ocr = " ".join(reader.readtext(gray, detail=0))
            procesar_con_ia(texto_ocr)
            st.rerun()

    with tab2:
        # Usamos el key='dictado_input' para que Streamlit guarde el texto automáticamente
        st.text_area("Pega el dictado aquí:", key="dictado_input", height=150)
        
        if st.button("Procesar con DeepSeek 🚀", use_container_width=True):
            texto_a_enviar = st.session_state.dictado_input
            if texto_a_enviar.strip():
                procesar_con_ia(texto_a_enviar)
                st.rerun()
            else:
                st.warning("Escribe o pega algo primero.")

with col2:
    st.subheader("📝 Verificación")
    with st.form("form_registro"):
        v_nom = st.text_input("Nombre", value=st.session_state.temp_datos['n'])
        v_tel = st.text_input("WhatsApp", value=st.session_state.temp_datos['t'])
        v_dir = st.text_input("Dirección", value=st.session_state.temp_datos['d'])
        
        if st.form_submit_button("✅ GUARDAR PEDIDO", use_container_width=True):
            if v_nom and v_tel:
                st.session_state.base_datos.append({
                    "Fecha": datetime.now().strftime("%H:%M"),
                    "Cliente": v_nom, "Tel": v_tel, "Dir": v_dir
                })
                st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}
                st.session_state.dictado_input = "" # Limpiar dictado
                st.success("Guardado.")
                st.rerun()

# --- TABLA ---
if st.session_state.base_datos:
    st.divider()
    df = pd.DataFrame(st.session_state.base_datos)
    st.dataframe(df, use_container_width=True)
