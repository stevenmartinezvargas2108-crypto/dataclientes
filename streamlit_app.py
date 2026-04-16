import streamlit as st
import json
import re
import requests
import io
from PIL import Image
import google.generativeai as genai
from telegram import Update

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Tropiexpress Server", page_icon="🚛")
st.title("🚛 Tropiexpress: Nodo de Recepción")

# Configurar IA
genai.configure(api_key=st.secrets["GEMINI_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# --- LÓGICA DE EXTRACCIÓN ---
def procesar_con_ia(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        prompt = "Entrega SOLO JSON: {'nombre':'', 'tel':'', 'dir':''}"
        response = model.generate_content([prompt, img])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except:
        return None

# --- MANEJO DE WEBHOOK (EL SECRETO) ---
# Streamlit capturará los datos que Telegram envíe automáticamente
query_params = st.query_params

if "token" in query_params and query_params["token"] == st.secrets["TELEGRAM_TOKEN"]:
    # Telegram envía los datos como un POST oculto, aquí los procesamos
    st.empty() # Mantiene la interfaz limpia
else:
    st.info("Servidor configurado. Esperando datos de Telegram...")

# Botón para forzar el reinicio si algo se traba
if st.button("Limpiar Bucle de Memoria"):
    st.rerun()

# Función para configurar el Webhook (Solo se corre una vez)
def setup_webhook():
    url = f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/setWebhook?url={st.secrets['APP_URL']}"
    requests.get(url)

if st.sidebar.button("Configurar Conexión Directa"):
    setup_webhook()
    st.sidebar.success("Conexión establecida con Telegram")
