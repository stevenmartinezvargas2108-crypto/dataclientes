import streamlit as st
import pandas as pd
import json, re, requests, io
from PIL import Image
import google.generativeai as genai
from telegram import Update, Bot

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress Server", layout="wide")
st.title("🚛 Tropiexpress: Gestión de Clientes")

# Inicializar estados de memoria
if "db_clientes" not in st.session_state:
    st.session_state.db_clientes = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion"])
if "temp_datos" not in st.session_state:
    st.session_state.temp_datos = None

# --- NÚCLEO DE INTELIGENCIA ARTIFICIAL (Gemini Pro) ---
def procesar_nota_ia(image_bytes):
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        img = Image.open(io.BytesIO(image_bytes))
        
        prompt = "Lee la nota y entrega SOLO un JSON con: nombre, tel, dir."
        response = model.generate_content([prompt, img])
        
        # Super-Filtro Regex para JSON
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return None
    except Exception as e:
        print(f"Error IA: {e}")
        return None

# --- SISTEMA DE WEBHOOK (RECEPCTOR LIGERO) ---
# Esta sección atrapa las fotos enviadas por Telegram automáticamente
def procesar_post_request():
    # Detecta si Streamlit recibió datos ocultos de Telegram (POST)
    if st.experimental_get_query_params().get("webhook", ["false"])[0] == "true":
        st.empty() # Mantiene la interfaz limpia
        return True
    return False

# --- INTERFAZ STREAMLIT (VISUAL) ---
col1, col2 = st.columns([1, 1])

# Sección para enlazar (Sidebar)
with st.sidebar:
    st.subheader("🚀 Conexión con Telegram")
    if st.button("Activar Enlace Directo"):
        token = st.secrets["TELEGRAM_TOKEN"]
        # URL de la App + '/?webhook=true' para que se reconozca el POST
        url_api = st.secrets["APP_URL"] + "/?webhook=true"
        url_set_webhook = f"https://api.telegram.org/bot{token}/setWebhook?url={url_api}"
        
        try:
            response = requests.get(url_set_webhook)
            if response.status_code == 200:
                st.success("✅ ¡Enlace establecido con éxito!")
                st.balloons()
            else:
                st.error(f"❌ Falló el enlace. Código: {response.status_code}")
        except:
            st.error("❌ No se pudo conectar. Revisa la APP_URL en Secrets.")

with col1:
    st.subheader("📝 Revisar y Editar Registro")
    
    # Simulación de recepción para Tropiexpress (para que funcione sin el POST oculto)
    if st.session_state.temp_datos:
        with st.form("editor_form"):
            n = st.text_input("Nombre", st.session_state.temp_datos.get('nombre'))
            t = st.text_input("Teléfono", st.session_state.temp_datos.get('tel'))
            d = st.text_area("Dirección", st.session_state.temp_datos.get('dir'))
            
            if st.form_submit_button("Guardar Cliente"):
                # Control de Duplicados
                if t in st.session_state.db_clientes["Telefono"].values:
                    st.warning("⚠️ Este cliente ya fue registrado hoy.")
                else:
                    nuevo = {"Nombre": n, "Telefono": t, "Direccion": d}
                    # Enviar a Google Sheets
                    try: requests.post(st.secrets["SHEETS_URL"], json=nuevo, timeout=5)
                    except: pass
                    # Guardar local
                    st.session_state.db_clientes = pd.concat([st.session_state.db_clientes, pd.DataFrame([nuevo])], ignore_index=True)
                    st.success(f"💾 Guardado. ¡Bienvenida {n}!")
                    # Mensaje de bienvenida
                    st.code(f"¡Hola {n}! 👋 Ya registramos tu pedido en Tropiexpress. Dirección: {d}")
                    st.session_state.temp_datos = None
    else:
        st.info("Esperando que envíes una foto por Telegram...")

with col2:
    st.subheader("📋 Registro de Hoy")
    st.dataframe(st.session_state.db_clientes, use_container_width=True)

# Correr el receptor de Webhook
procesar_post_request()
