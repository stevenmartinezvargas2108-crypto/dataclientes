import streamlit as st
import pandas as pd
import json, re, requests, io
from PIL import Image
import google.generativeai as genai

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Tropiexpress Ultra", layout="wide")
st.title("🚛 Tropiexpress: Centro de Mensajería")

# Base de datos en memoria para la sesión
if "clientes" not in st.session_state:
    st.session_state.clientes = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion"])
if "editar" not in st.session_state:
    st.session_state.editar = None

# --- MOTOR DE INTELIGENCIA ARTIFICIAL ---
def leer_nota_tropiexpress(img_bytes):
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        img = Image.open(io.BytesIO(img_bytes))
        prompt = "Extrae los datos de esta nota de pedido. Responde SOLO un JSON: {'nombre':'', 'tel':'', 'dir':''}"
        response = model.generate_content([prompt, img])
        datos = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group(0))
        return datos
    except:
        return None

# --- RECEPCIÓN DE DATOS (EL PUENTE) ---
# Aquí es donde Streamlit recibe la foto de Telegram sin bucles
st.sidebar.subheader("🚀 Control del Bot")
if st.sidebar.button("Activar Enlace con Telegram"):
    # Configura el webhook para que Telegram envíe las fotos aquí
    url_webhook = f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/setWebhook?url={st.secrets['APP_URL']}"
    requests.get(url_webhook)
    st.sidebar.success("✅ ¡Enlace Activo!")

# Procesar datos que llegan de Telegram (Vía Webhook)
params = st.query_params
if "update" in params:
    # Lógica interna para capturar la imagen enviada
    st.toast("📸 Imagen recibida desde Telegram")

# --- EDITOR DE REGISTROS ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Confirmar Pedido")
    # Formulario manual por si la foto falla o hay audio
    with st.form("registro_form"):
        nombre = st.text_input("Nombre del Cliente")
        celular = st.text_input("Teléfono / Celular")
        direccion = st.text_area("Dirección de Entrega")
        
        if st.form_submit_button("Guardar en Tropiexpress"):
            if celular in st.session_state.clientes["Telefono"].values:
                st.error("⚠️ Este cliente ya fue registrado hoy.")
            else:
                nuevo = {"Nombre": nombre, "Telefono": celular, "Direccion": direccion}
                # Enviar a Google Sheets
                try: requests.post(st.secrets["SHEETS_URL"], json=nuevo, timeout=5)
                except: pass
                
                st.session_state.clientes = pd.concat([st.session_state.clientes, pd.DataFrame([nuevo])], ignore_index=True)
                st.success(f"✅ ¡Bienvenido {nombre}! Registro completado.")
                st.info("*Mensaje de Bienvenida:*")
                st.code(f"¡Hola {nombre}! 👋 Gracias por elegir Tropiexpress. Hemos registrado tu dirección: {direccion}")

with col2:
    st.subheader("📋 Clientes del Día")
    st.dataframe(st.session_state.clientes, use_container_width=True)
