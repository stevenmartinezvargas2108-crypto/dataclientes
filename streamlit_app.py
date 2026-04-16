import streamlit as st
import pandas as pd
import json, re, requests, io
from PIL import Image
import google.generativeai as genai

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Tropiexpress Ultra", layout="wide")
st.title("🚛 Tropiexpress: Centro de Mensajería")

# Verificar que todos los secretos existan antes de arrancar
try:
    token = st.secrets["TELEGRAM_TOKEN"]
    ai_key = st.secrets["GEMINI_KEY"]
    app_url = st.secrets["APP_URL"]
    sheet = st.secrets["SHEETS_URL"]
except Exception as e:
    st.error(f"⚠️ Falta configurar un Secret: {e}")
    st.stop()

# Inicializar base de datos en la sesión
if "clientes" not in st.session_state:
    st.session_state.clientes = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion"])

# --- MOTOR DE IA ---
def procesar_ia(img_bytes):
    try:
        genai.configure(api_key=ai_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        img = Image.open(io.BytesIO(img_bytes))
        prompt = "Responde SOLO JSON con: {'nombre':'', 'tel':'', 'dir':''}"
        response = model.generate_content([prompt, img])
        return json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group(0))
    except: return None

# --- SIDEBAR: CONTROL DE ENLACE ---
with st.sidebar:
    st.subheader("🚀 Conexión Telegram")
    if st.button("Re-conectar Bot"):
        # Esto soluciona el KeyError de tu imagen 1000947675.jpg
        webhook_res = requests.get(f"https://api.telegram.org/bot{token}/setWebhook?url={app_url}")
        if webhook_res.status_code == 200:
            st.success("Enlace establecido")
        else:
            st.error("Error al conectar")

# --- CUERPO PRINCIPAL (EDICIÓN Y REGISTRO) ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Nuevo Registro")
    with st.form("registro"):
        n = st.text_input("Nombre")
        t = st.text_input("Teléfono")
        d = st.text_area("Dirección")
        
        if st.form_submit_button("Guardar"):
            if t in st.session_state.clientes["Telefono"].values:
                st.warning("El cliente ya existe.")
            else:
                nuevo = {"Nombre": n, "Telefono": t, "Direccion": d}
                requests.post(sheet, json=nuevo)
                st.session_state.clientes = pd.concat([st.session_state.clientes, pd.DataFrame([nuevo])], ignore_index=True)
                st.success(f"Guardado. Bienvenida {n}")
                st.code(f"¡Hola {n}! Ya registramos tu pedido en {d}")

with col2:
    st.subheader("📋 Historial")
    st.dataframe(st.session_state.clientes, use_container_width=True)
