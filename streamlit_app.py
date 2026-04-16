import streamlit as st
import pandas as pd
import json, re, requests, io
from PIL import Image
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tropiexpress Ultra", layout="wide")
st.title("🚛 Tropiexpress: Gestión de Clientes")

# Inicializar Base de Datos Local en la sesión
if "db_clientes" not in st.session_state:
    st.session_state.db_clientes = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion", "Estado"])
if "temp_datos" not in st.session_state:
    st.session_state.temp_datos = None

# --- FUNCIONES DE IA ---
def procesar_nota(image_bytes):
    genai.configure(api_key=st.secrets["GEMI…
[8:24 a.m., 16/4/2026] Jhonnathan: import streamlit as st
import pandas as pd
import json, re, requests, io
from PIL import Image
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tropiexpress Ultra", layout="wide")
st.title("🚛 Tropiexpress: Gestión de Clientes")

# Inicializar Base de Datos Local en la sesión
if "db_clientes" not in st.session_state:
    st.session_state.db_clientes = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion", "Estado"])
if "temp_datos" not in st.session_state:
    st.session_state.temp_datos = None

# --- FUNCIONES DE IA ---
def procesar_nota(image_bytes):
    genai.configure(api_key=st.secrets["GEMINI_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    img = Image.open(io.BytesIO(image_bytes))
    prompt = "Extrae Nombre, Teléfono y Dirección. Responde SOLO JSON: {'nombre':'', 'tel':'', 'dir':''}"
    try:
        response = model.generate_content([prompt, img])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group(0))
    except: return None

# --- LÓGICA DEL BOT ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Tropiexpress: Leyendo nota...")
    file = await update.message.photo[-1].get_file()
    img_bytes = await file.download_as_bytearray()
    datos = procesar_nota(img_bytes)
    
    if datos:
        datos['tel'] = ''.join(filter(str.isdigit, str(datos['tel'])))
        st.session_state.temp_datos = datos
        await update.message.reply_text(f"✅ Datos listos en la App para revisar: {datos['nombre']}")
    else:
        await update.message.reply_text("❌ Error al leer. Prueba con audio.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎤 Audio recibido. Procésalo manualmente en la App.")

# --- INTERFAZ STREAMLIT (EDICIÓN Y GUARDADO) ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Editor de Registro")
    if st.session_state.temp_datos:
        with st.form("editor"):
            nome = st.text_input("Nombre", st.session_state.temp_datos['nombre'])
            tele = st.text_input("Teléfono", st.session_state.temp_datos['tel'])
            dire = st.text_input("Dirección", st.session_state.temp_datos['dir'])
            
            if st.form_submit_button("Confirmar y Enviar"):
                # Verificar si ya existe (No repetir clientes)
                if tele in st.session_state.db_clientes["Telefono"].values:
                    st.warning("⚠️ Este cliente ya está registrado.")
                else:
                    nuevo = {"Nombre": nome, "Telefono": tele, "Direccion": dire, "Estado": "Nuevo"}
                    # Enviar a Sheets
                    requests.post(st.secrets["SHEETS_URL"], json=nuevo)
                    # Guardar en App
                    st.session_state.db_clientes = pd.concat([st.session_state.db_clientes, pd.DataFrame([nuevo])], ignore_index=True)
                    st.success(f"💾 Guardado. ¡Bienvenido {nome}!")
                    # Mensaje de bienvenida para copiar
                    st.code(f"¡Hola {nome}! Bienvendio a Tropiexpress. Ya registramos tu dirección: {dire}")
                    st.session_state.temp_datos = None
    else:
        st.info("Esperando foto o audio desde Telegram...")

with col2:
    st.subheader("📊 Clientes Registrados")
    st.dataframe(st.session_state.db_clientes, use_container_width=True)

# --- ARRANQUE SEGURO ---
if st.sidebar.button("🚀 Iniciar Servidor Bot"):
    app = Application.builder().token(st.secrets["TELEGRAM_TOKEN"]).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    st.sidebar.success("Bot escuchando...")
    app.run_polling(drop_pending_updates=True)
