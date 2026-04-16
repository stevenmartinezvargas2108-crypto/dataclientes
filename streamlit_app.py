import streamlit as st
import pandas as pd
import json, re, requests, io
from PIL import Image
import google.generativeai as genai

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress Ultra", layout="wide")
st.title("🚛 Tropiexpress: Nodo Central")

# Inicializar memoria
if "clientes" not in st.session_state:
    st.session_state.clientes = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion"])
if "temp_datos" not in st.session_state:
    st.session_state.temp_datos = None

# --- LÓGICA DE IA ---
def leer_con_gemini(img_bytes):
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        img = Image.open(io.BytesIO(img_bytes))
        prompt = "Extrae Nombre, Tel y Dir. Responde SOLO JSON: {'nombre':'', 'tel':'', 'dir':''}"
        response = model.generate_content([prompt, img])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except: return None

# --- SOLUCIÓN AL ATTRIBUTEERROR ---
# Usamos la nueva forma de leer parámetros de Streamlit
params = st.query_params
if "webhook" in params and params["webhook"] == "true":
    st.toast("⚡ Conexión de Telegram detectada")

# --- INTERFAZ ---
with st.sidebar:
    st.subheader("🚀 Enlace Telegram")
    if st.button("Activar Webhook"):
        # Esto configura Telegram para que envíe fotos aquí
        url = f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/setWebhook?url={st.secrets['APP_URL']}/?webhook=true"
        requests.get(url)
        st.success("Enlace configurado")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Validar Datos")
    # Formulario para editar antes de guardar
    with st.form("registro"):
        nom = st.text_input("Nombre")
        tel = st.text_input("Teléfono")
        dir = st.text_area("Dirección")
        
        if st.form_submit_button("Guardar en Tropiexpress"):
            if tel in st.session_state.clientes["Telefono"].values:
                st.error("Cliente ya registrado.")
            else:
                nuevo = {"Nombre": nom, "Telefono": tel, "Direccion": dir}
                # Enviar a Sheets
                try: requests.post(st.secrets["SHEETS_URL"], json=nuevo, timeout=5)
                except: pass
                # Guardar local
                st.session_state.clientes = pd.concat([st.session_state.clientes, pd.DataFrame([nuevo])], ignore_index=True)
                st.success(f"Registrado: {nom}")
                st.code(f"¡Hola {nom}! Bienvenido a Tropiexpress. Tu pedido va para: {dir}")

with col2:
    st.subheader("📋 Registro de Hoy")
    st.dataframe(st.session_state.clientes, use_container_width=True)
