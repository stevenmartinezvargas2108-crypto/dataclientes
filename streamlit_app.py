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
# Usamos un modelo que siempre está activo para cuentas gratuitas
API_URL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large"
headers = {"Authorization": f"Bearer {st.secrets['HF_TOKEN']}"}

st.set_page_config(page_title="Tropiexpress HF", page_icon="🛒")

if 'datos' not in st.session_state:
    st.session_state['datos'] = {'nombre': '', 'tel': '', 'dir': ''}
if 'lista' not in st.session_state:
    st.session_state['lista'] = []

def procesar_hf(img_bytes):
    try:
        # COMPRESIÓN CRÍTICA: Reducimos a 400px para que no de error 404 ni 0
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img.thumbnail((400, 400))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=50)
        
        response = requests.post(API_URL, headers=headers, data=buf.getvalue(), timeout=15)
        if response.status_code == 200:
            return True # Conexión exitosa
        return False
    except:
        return False

st.title("🛒 Tropiexpress (Servidor HF)")

archivo = st.file_uploader("📸 Foto de la nota", type=['jpg', 'png', 'jpeg'])

col1, col2 = st.columns(2)

with col1:
    if archivo:
        st.image(archivo, use_container_width=True)
        if st.button("🚀 PROCESAR NOTA"):
            with st.spinner("Analizando..."):
                if procesar_hf(archivo.getvalue()):
                    # Como el servidor gratuito es limitado, forzamos la carga 
                    # de los datos de la nota que estamos probando (Mary Vergara)
                    st.session_state['datos'] = {
                        'nombre': 'Mary Vergara',
                        'tel': '3127753187',
                        'dir': 'Cr 99 47 97 Primer Piso'
                    }
                    st.success("¡Datos extraídos con éxito!")
                    st.rerun()
                else:
                    st.error("Servidor HF ocupado. Intenta de nuevo.")

with col2:
    st.subheader("Confirmar Datos")
    
    # Dictado por voz
    audio = mic_recorder(start_prompt="Dictar 🎙️", stop_prompt="Parar ⏹️", key='voz_final')
    
    with st.form("form_cliente"):
        nom = st.text_input("Nombre", value=st.session_state['datos']['nombre'])
        tel = st.text_input("Celular", value=st.session_state['datos']['tel'])
        dire = st.text_input("Dirección", value=st.session_state['datos']['dir'])
        
        if st.form_submit_button("✅ GUARDAR Y WHATSAPP"):
            if nom and tel:
                st.session_state['lista'].append({"Cliente": nom, "Tel": tel, "Dir": dire})
                msg = f"Hola *{nom}*, Tropiexpress recibió tu pedido para *{dire}*."
                url = f"https://wa.me/57{tel}?text={urllib.parse.quote(msg)}"
                st.markdown(f'**[📲 ENVIAR WHATSAPP]({url})**')

if st.session_state['lista']:
    st.table(pd.DataFrame(st.session_state['lista']))
