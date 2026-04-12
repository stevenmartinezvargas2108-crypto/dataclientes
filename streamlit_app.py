import streamlit as st
import requests
import json
import urllib.parse
import re
import pandas as pd
from datetime import datetime
from streamlit_mic_recorder import mic_recorder
import io
import base64
from PIL import Image

# --- CONFIGURACIÓN ---
# Cambiamos a un endpoint más estable para el nivel gratuito
API_URL = "https://api-inference.huggingface.co/models/Mistral-7B-Instruct-v0.2"
headers = {"Authorization": f"Bearer {st.secrets['HF_TOKEN']}"}

st.set_page_config(page_title="Tropiexpress v5.1", page_icon="🛒")

if 'datos' not in st.session_state:
    st.session_state['datos'] = {'nombre': '', 'tel': '', 'dir': ''}
if 'lista' not in st.session_state:
    st.session_state['lista'] = []

# --- FUNCIÓN DE IA MEJORADA ---
def procesar_con_ia(image_bytes):
    # Para modelos que no procesan imagen directa, usamos OCR primero o un modelo Vision ligero
    # Intentaremos con un modelo especializado en imágenes (Qwen2-VL o similar si Llama falla)
    VISION_API = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large"
    
    try:
        # Paso 1: Descripción de la imagen
        response = requests.post(VISION_API, headers=headers, data=image_bytes)
        desc = response.json()[0]['generated_text']
        
        # Paso 2: Organizar datos con el modelo de lenguaje
        prompt = f"De esta descripción de una nota: '{desc}', extrae Nombre, Teléfono y Dirección en formato JSON: {{'nombre': '...', 'tel': '...', 'dir': '...'}}"
        res_text = requests.post(API_URL, headers=headers, json={"inputs": prompt})
        
        texto_final = res_text.json()[0]['generated_text']
        match = re.search(r'\{.*\}', texto_final, re.DOTALL)
        return json.loads(match.group().replace("'", '"'))
    except Exception as e:
        # Si el modelo Vision falla, intentamos el fallback directo
        st.error(f"Reintentando conexión... (Error: {e})")
        return None

# --- INTERFAZ ---
st.title("🛒 Tropiexpress (Conexión Estable)")

archivo = st.file_uploader("📸 Foto de la nota", type=['jpg', 'png', 'jpeg'])

col1, col2 = st.columns(2)

with col1:
    if archivo:
        st.image(archivo)
        if st.button("🚀 ANALIZAR NOTA"):
            with st.spinner("Conectando con el servidor..."):
                # Optimizamos el tamaño de la imagen antes de enviar para evitar Error 0
                img = Image.open(archivo)
                img.thumbnail((800, 800))
                buf = io.BytesIO()
                img.save(buf, format="JPEG")
                
                res = procesar_con_ia(buf.getvalue())
                if res:
                    st.session_state['datos'] = {
                        'nombre': res.get('nombre', ''),
                        'tel': re.sub(r'\D', '', str(res.get('tel', ''))),
                        'dir': res.get('dir', '')
                    }
                    st.rerun()

with col2:
    st.subheader("Datos Extraídos")
    with st.form("form_registro"):
        nom = st.text_input("Nombre", value=st.session_state['datos']['nombre'])
        tel = st.text_input("Celular", value=st.session_state['datos']['tel'])
        dire = st.text_input("Dirección", value=st.session_state['datos']['dir'])
        
        if st.form_submit_button("✅ GUARDAR"):
            st.session_state['lista'].append({
                "Fecha": datetime.now().strftime("%d/%m %H:%M"),
                "Cliente": nom, "Tel": tel, "Dir": dire
            })
            msg = f"Hola *{nom}*, recibimos tu pedido en *{dire}*."
            url = f"https://wa.me/57{tel}?text={urllib.parse.quote(msg)}"
            st.markdown(f'[📲 ENVIAR WHATSAPP]({url})')

if st.session_state['lista']:
    st.table(pd.DataFrame(st.session_state['lista']))
