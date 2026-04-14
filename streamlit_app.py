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
st.set_page_config(page_title="TropiExpress v13.0 (DEBUG)", page_icon="🛒", layout="wide")

# Inicializar estados
if 'base_datos' not in st.session_state:
    st.session_state.base_datos = []
if 'temp_datos' not in st.session_state:
    st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}

# --- CONEXIÓN IA ---
def obtener_cliente():
    try:
        if "DEEPSEEK_API_KEY" not in st.secrets:
            st.error("❌ ERROR: No se encontró la llave 'DEEPSEEK_API_KEY' en los Secrets de Streamlit.")
            return None
        return OpenAI(
            api_key=st.secrets["DEEPSEEK_API_KEY"],
            base_url="https://api.deepseek.com"
        )
    except Exception as e:
        st.error(f"❌ ERROR DE CONFIGURACIÓN: {e}")
        return None

client = obtener_cliente()

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False)

reader = load_ocr()

# --- FUNCIÓN MAESTRA CON DEBUG ---
def procesar_con_ia(texto_crudo):
    if not client: return

    # Prompt ultra-rígido
    prompt = f"""
    Extrae: "{texto_crudo}"
    Respuesta requerida (JSON PURO):
    {{
      "nombre": "Nombre del cliente",
      "telefono": "10 dígitos",
      "direccion": "DIRECCION COMPLETA"
    }}
    """

    with st.spinner("🧠 DeepSeek pensando..."):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Eres un convertidor de texto a JSON. No hables, solo entrega el JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            # 1. Capturar respuesta
            res_raw = response.choices[0].message.content.strip()
            
            # MOSTRAR RESPUESTA PARA DEPURAR (BORRAR ESTO LUEGO)
            st.info(f"DEBUG - Respuesta de IA: {res_raw}")
            
            # 2. Limpiar JSON
            res_limpia = re.search(r'\{.*\}', res_raw, re.DOTALL)
            if res_limpia:
                json_data = json.loads(res_limpia.group())
                
                # 3. Guardar en Session State de forma explícita
                st.session_state.temp_datos['n'] = str(json_data.get('nombre', 'CLIENTE NUEVO')).title()
                st.session_state.temp_datos['t'] = str(json_data.get('telefono', ''))
                st.session_state.temp_datos['d'] = str(json_data.get('direccion', '')).upper()
                
                st.toast("✅ Datos listos para verificar", icon="🔔")
            else:
                st.error("La IA no devolvió un formato JSON válido.")

        except Exception as e:
            st.error(f"❌ ERROR EN LA LLAMADA: {e}")

# --- INTERFAZ ---
st.title("🛒 TropiExpress v13.0 (Modo Debug)")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📥 Entrada")
    tab1, tab2 = st.tabs(["📸 Foto", "🎙️ Dictado"])
    
    with tab1:
        foto = st.file_uploader("Subir", type=['jpg', 'png'])
        if foto and st.button("Procesar Foto", key="btn_foto"):
            img = Image.open(foto)
            img = ImageOps.exif_transpose(img)
            img.thumbnail((700, 700))
            texto_ocr = " ".join(reader.readtext(np.array(img), detail=0))
            procesar_con_ia(texto_ocr)
            st.rerun()

    with tab2:
        # Usamos un campo de texto con nombre fijo
        input_voz = st.text_area("Pega el texto:", placeholder="Ej: Juan 310...", height=150)
        
        if st.button("Procesar Dictado 🚀", key="btn_dictado"):
            if input_voz.strip():
                procesar_con_ia(input_voz)
                st.rerun()
            else:
                st.warning("Escribe algo primero.")

with col2:
    st.subheader("📝 Verificación")
    # IMPORTANTE: Aquí los valores vienen directamente del session_state
    with st.form("form_final"):
        f_nom = st.text_input("Nombre", value=st.session_state.temp_datos['n'])
        f_tel = st.text_input("Teléfono", value=st.session_state.temp_datos['t'])
        f_dir = st.text_input("Dirección", value=st.session_state.temp_datos['d'])
        
        if st.form_submit_button("✅ GUARDAR EN TABLA"):
            if f_nom and f_tel:
                st.session_state.base_datos.append({
                    "Hora": datetime.now().strftime("%H:%M"),
                    "Cliente": f_nom, "Tel": f_tel, "Dir": f_dir
                })
                # Limpiar todo
                st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}
                st.success("¡Pedido guardado!")
                st.rerun()

# --- TABLA ---
if st.session_state.base_datos:
    st.divider()
    st.dataframe(pd.DataFrame(st.session_state.base_datos), use_container_width=True)
