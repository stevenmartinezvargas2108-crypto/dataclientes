import streamlit as st
import pandas as pd
from datetime import datetime
import json
import re
import io
from PIL import Image, ImageOps
import numpy as np
from openai import OpenAI

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="TropiExpress v13.0", page_icon="🛒")

if 'temp_datos' not in st.session_state:
    st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}
if 'base_datos' not in st.session_state:
    st.session_state.base_datos = []

# --- IA Y LOGICA ---
def conectar_ia():
    if "DEEPSEEK_API_KEY" not in st.secrets:
        st.error("Configura DEEPSEEK_API_KEY en Secrets.")
        return None
    return OpenAI(api_key=st.secrets["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")

client = conectar_ia()

def procesar_con_ia(texto):
    if not client: return
    prompt = f"JSON con nombre, telefono, direccion de: {texto}"
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        res = response.choices[0].message.content
        match = re.search(r'\{.*\}', res, re.DOTALL)
        if match:
            datos = json.loads(match.group())
            st.session_state.temp_datos['n'] = str(datos.get('nombre', '')).title()
            st.session_state.temp_datos['t'] = str(datos.get('telefono', ''))
            st.session_state.temp_datos['d'] = str(datos.get('direccion', '')).upper()
            return True
    except Exception as e:
        st.error(f"Error IA: {e}")
    return False

# --- INTERFAZ ---
st.title("🛒 TropiExpress IA Total")

tab1, tab2 = st.tabs(["🎙️ Dictado / Texto", "📸 Subir Foto"])

with tab1:
    entrada = st.text_area("Pega el pedido aquí:", height=100)
    if st.button("PROCESAR TEXTO 🚀"):
        if entrada and procesar_con_ia(entrada):
            st.rerun()

with tab2:
    foto = st.file_uploader("Sube la foto de la nota", type=['jpg', 'jpeg', 'png'])
    if foto:
        if st.button("LEER IMAGEN CON IA"):
            with st.spinner("Leyendo imagen (esto puede tardar unos segundos)..."):
                # Importamos EasyOCR solo aquí para no saturar el inicio
                import easyocr
                reader = easyocr.Reader(['es'], gpu=False)
                
                # Comprimir para evitar error de memoria
                img = Image.open(foto)
                img = ImageOps.exif_transpose(img)
                img.thumbnail((700, 700))
                
                # OCR
                resultados = reader.readtext(np.array(img.convert("RGB")), detail=0)
                texto_ocr = " ".join(resultados)
                
                if procesar_con_ia(texto_ocr):
                    st.rerun()

st.divider()

# --- VERIFICACIÓN ---
st.subheader("📝 Verificación")
with st.form("registro"):
    c_nom = st.text_input("Nombre", value=st.session_state.temp_datos['n'])
    c_tel = st.text_input("Teléfono", value=st.session_state.temp_datos['t'])
    c_dir = st.text_input("Dirección", value=st.session_state.temp_datos['d'])
    
    if st.form_submit_button("✅ GUARDAR PEDIDO", use_container_width=True):
        if c_nom and c_tel:
            st.session_state.base_datos.append({
                "Cliente": c_nom, "Tel": c_tel, "Dir": c_dir, "Hora": datetime.now().strftime("%H:%M")
            })
            st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}
            st.success("¡Guardado!")
            st.rerun()

if st.session_state.base_datos:
    st.table(pd.DataFrame(st.session_state.base_datos))
