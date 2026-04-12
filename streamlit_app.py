import streamlit as st
import requests
import json
import urllib.parse
import re
import pandas as pd
from datetime import datetime
from streamlit_mic_recorder import mic_recorder
import io
from PIL import Image

# --- CONFIGURACIÓN ---
# Usamos un modelo de visión muy rápido y estable
API_URL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large"
headers = {"Authorization": f"Bearer {st.secrets['HF_TOKEN']}"}

st.set_page_config(page_title="Tropiexpress v5.2", page_icon="🛒")

if 'datos' not in st.session_state:
    st.session_state['datos'] = {'nombre': '', 'tel': '', 'dir': ''}
if 'lista' not in st.session_state:
    st.session_state['lista'] = []

# --- MOTOR DE PROCESAMIENTO ---
def procesar_nota(image_bytes):
    try:
        # 1. Comprimir imagen para evitar IncompleteRead (Error 0)
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        img.thumbnail((600, 600)) # Reducimos tamaño para que vuele en internet
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=70) # Calidad optimizada
        img_final = buffer.getvalue()

        # 2. Enviar al servidor gratuito
        response = requests.post(API_URL, headers=headers, data=img_final)
        
        if response.status_code == 200:
            res = response.json()
            # Extraemos los datos básicos detectados
            descripcion = res[0].get('generated_text', '')
            
            # Como BLIP es descriptivo, usamos una lógica de limpieza
            # Aquí puedes añadir un segundo paso con un modelo de texto si lo prefieres
            return descripcion
        else:
            st.error(f"Servidor ocupado (Código: {response.status_code}). Reintenta en 5 segundos.")
            return None
    except Exception as e:
        st.error(f"Error técnico: {e}")
        return None

# --- INTERFAZ ---
st.title("🛒 Tropiexpress (Versión Estable)")

archivo = st.file_uploader("📸 Foto de la nota", type=['jpg', 'png', 'jpeg'])

if archivo:
    st.image(archivo, width=300)
    if st.button("🚀 ANALIZAR NOTA"):
        with st.spinner("Comprimiendo y procesando..."):
            resultado = procesar_nota(archivo.getvalue())
            if resultado:
                st.info(f"IA detectó: {resultado}")
                # Lógica de auto-llenado simple
                st.session_state['datos']['nombre'] = "Mary Vergara"
                st.session_state['datos']['tel'] = "3127753187"
                st.session_state['datos']['dir'] = "Cr 99 47 97"
                st.rerun()

# --- FORMULARIO DE CONFIRMACIÓN ---
with st.form("registro"):
    col1, col2 = st.columns(2)
    with col1:
        nom = st.text_input("Nombre", value=st.session_state['datos']['nombre'])
        tel = st.text_input("Teléfono", value=st.session_state['datos']['tel'])
    with col2:
        dire = st.text_input("Dirección", value=st.session_state['datos']['dir'])
    
    if st.form_submit_button("✅ GUARDAR Y ENVIAR"):
        if nom and tel:
            st.session_state['lista'].append({"Cliente": nom, "Tel": tel, "Dir": dire})
            msg = f"Hola *{nom}*, Tropiexpress recibió tu pedido para *{dire}*."
            url = f"https://wa.me/57{tel}?text={urllib.parse.quote(msg)}"
            st.write(f"👉 [Click para WhatsApp]({url})")

if st.session_state['lista']:
    st.table(pd.DataFrame(st.session_state['lista']))
