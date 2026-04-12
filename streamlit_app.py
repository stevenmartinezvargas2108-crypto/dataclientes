import streamlit as st
import PIL.Image
import json
import urllib.parse
import re
import pandas as pd
from io import BytesIO
import base64
from groq import Groq # Cambiamos de google.generativeai a groq

# --- 1. CONFIGURACIÓN DE SEGURIDAD ---
try:
    # Cambia el nombre en tus Secrets de Streamlit a GROQ_API_KEY
    API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    API_KEY = "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" 

client = Groq(api_key=API_KEY)

# --- 2. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress Ultra-Extract", page_icon="🛒", layout="wide")

if 'db_clientes' not in st.session_state:
    st.session_state['db_clientes'] = []

# Función para codificar la imagen
def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

# --- 3. LÓGICA CON LLAMA 3 (GROQ) ---
def analizar_con_groq(imagen_bytes):
    if not API_KEY:
        st.error("❌ Falta la GROQ_API_KEY en los Secrets.")
        return None
        
    try:
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        
        # Usamos Llama 3.2 Vision de 11B o 90B
        completion = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extrae de esta nota: nombre, tel, dir y urgencia. Responde solo en JSON."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        st.error(f"Error con Groq: {e}")
        return None

# --- EL RESTO DEL CÓDIGO (Interfaz y WhatsApp) SIGUE IGUAL ---
st.title("🛒 Tropiexpress AI (Llama 3 Edition)")
archivo = st.file_uploader("Sube la nota", type=['jpg', 'jpeg', 'png'])

if archivo:
    bytes_data = archivo.getvalue()
    st.image(bytes_data, width=350)
    
    if st.button("🚀 PROCESAR AHORA"):
        with st.spinner("Leyendo con Llama 3..."):
            resultado = analizar_con_groq(bytes_data)
            if resultado:
                # Aquí actualizas tus campos de formulario como antes
                st.success("¡Datos extraídos!")
                st.json(resultado)
