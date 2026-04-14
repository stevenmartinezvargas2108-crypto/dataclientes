import streamlit as st
import pandas as pd
from datetime import datetime
import json
import re
import io
from PIL import Image, ImageOps
import google.generativeai as genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="TropiExpress v25", page_icon="🛒")

if 'temp' not in st.session_state:
    st.session_state.temp = {'n': '', 't': '', 'd': ''}
if 'db' not in st.session_state:
    st.session_state.db = []

# --- FUNCIÓN IA BLINDADA ---
def procesar_con_gemini(texto_prompt, imagen=None):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Usamos el nombre del modelo más estable posible
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Enviamos el contenido
        if imagen:
            response = model.generate_content([texto_prompt, imagen])
        else:
            response = model.generate_content(texto_prompt)
        
        # Limpiar respuesta
        txt = response.text
        match = re.search(r'\{.*\}', txt, re.DOTALL)
        if match:
            datos = json.loads(match.group())
            st.session_state.temp['n'] = str(datos.get('nombre', '')).title()
            st.session_state.temp['t'] = re.sub(r'\D', '', str(datos.get('telefono', '')))
            st.session_state.temp['d'] = str(datos.get('direccion', '')).upper()
            return True
    except Exception as e:
        st.error(f"Error de conexión: {e}")
    return False

# --- INTERFAZ ---
st.title("🛒 TropiExpress v25")

f = st.file_uploader("Sube foto", type=['jpg','jpeg'])
if f:
    if st.button("PROCESAR FOTO"):
        with st.spinner("Leyendo..."):
            img = Image.open(f)
            img = ImageOps.exif_transpose(img)
            img.thumbnail((600, 600)) # Muy ligero para no agotar memoria
            if procesar_con_gemini('Extrae JSON: {"nombre":"", "telefono":"", "direccion":""}', img):
                st.rerun()

# --- REGISTRO ---
with st.form("form"):
    n = st.text_input("Nombre", value=st.session_state.temp['n'])
    t = st.text_input("Teléfono", value=st.session_state.temp['t'])
    d = st.text_input("Dirección", value=st.session_state.temp['d'])
    if st.form_submit_button("GUARDAR"):
        st.session_state.db.insert(0, {"Nombre": n, "Tel": t, "Dir": d})
        st.session_state.temp = {'n': '', 't': '', 'd': ''}
        st.rerun()

# --- TABLA ---
if st.session_state.db:
    df = pd.DataFrame(st.session_state.db)
    st.dataframe(df)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar CSV", csv, "pedidos.csv", "text/csv")
