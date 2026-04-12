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

# --- CONFIGURACIÓN HUGGING FACE ---
# Usamos Llama 3.2 Vision: El modelo más potente y gratuito para leer imágenes.
API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-11B-Vision-Instruct"
headers = {"Authorization": f"Bearer {st.secrets['HF_TOKEN']}"}

st.set_page_config(page_title="Tropiexpress v5.0", page_icon="🛒")

# Inicialización de estados (Como en tu código original)
if 'datos' not in st.session_state:
    st.session_state['datos'] = {'nombre': '', 'tel': '', 'dir': ''}
if 'lista' not in st.session_state:
    st.session_state['lista'] = []

# --- FUNCIÓN DE IA (REEMPLAZA A GEMINI) ---
def procesar_con_huggingface(image_bytes):
    # Convertir imagen a Base64 para enviarla por internet
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    data_url = f"data:image/jpeg;base64,{base64_image}"
    
    prompt = "Extrae de esta nota de pedido: nombre, tel, dir. Responde ÚNICAMENTE un objeto JSON: {'nombre': '...', 'tel': '...', 'dir': '...'}"
    
    payload = {
        "inputs": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            }
        ],
        "parameters": {"max_new_tokens": 300}
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        resultado = response.json()
        texto_ia = resultado[0]['generated_text']
        
        # Extraer el JSON del texto usando Regex por seguridad
        match = re.search(r'\{.*\}', texto_ia, re.DOTALL)
        if match:
            return json.loads(match.group().replace("'", '"'))
    except Exception as e:
        st.error(f"Error de conexión con la IA: {e}")
        return None

# --- INTERFAZ (Tu estructura original) ---
st.title("🛒 Tropiexpress (Cerebro Llama 3.2)")

archivo = st.file_uploader("📸 Foto de la nota", type=['jpg', 'png', 'jpeg'])

col1, col2 = st.columns(2)

with col1:
    if archivo:
        st.image(archivo)
        if st.button("🚀 LEER NOTA CON IA"):
            with st.spinner("Leyendo manuscrito..."):
                res = procesar_con_huggingface(archivo.getvalue())
                if res:
                    st.session_state['datos'] = {
                        'nombre': res.get('nombre', ''),
                        # Limpiamos el teléfono para que solo queden números
                        'tel': re.sub(r'\D', '', str(res.get('tel', ''))),
                        'dir': res.get('dir', '')
                    }
                    st.rerun()

with col2:
    st.subheader("Confirmar Datos")
    
    # Dictado por voz
    audio = mic_recorder(start_prompt="Dictar 🎙️", stop_prompt="Parar ⏹️", key='voz_v5')
    if audio:
        st.info("Procesando dictado...")

    with st.form("form_cliente"):
        nom = st.text_input("Nombre", value=st.session_state['datos']['nombre'])
        tel = st.text_input("Celular", value=st.session_state['datos']['tel'])
        dire = st.text_input("Dirección", value=st.session_state['datos']['dir'])
        
        if st.form_submit_button("✅ GUARDAR Y ENVIAR"):
            st.session_state['lista'].append({
                "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"), 
                "Cliente": nom, 
                "Tel": tel, 
                "Dir": dire
            })
            # Link de WhatsApp automático
            msg = f"Hola {nom}, Tropiexpress recibió tu pedido. Lo enviaremos a {dire}."
            url = f"https://wa.me/57{tel}?text={urllib.parse.quote(msg)}"
            st.markdown(f'*[📲 CLICK AQUÍ PARA ENVIAR WHATSAPP]({url})*')

# Tabla de historial
if st.session_state['lista']:
    st.divider()
    st.table(pd.DataFrame(st.session_state['lista']))
