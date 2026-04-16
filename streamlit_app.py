import streamlit as st
import pandas as pd
import json, re, requests, io, asyncio, threading
from PIL import Image
import google.generativeai as genai
from telegram import Update, constants
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tropiexpress Server", layout="wide")
st.title("🚛 Tropiexpress: Nodo Central")

# Memoria de la aplicación
if "db_clientes" not in st.session_state:
    st.session_state.db_clientes = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion"])
if "temp_datos" not in st.session_state:
    st.session_state.temp_datos = None

# --- IA Y PROCESAMIENTO ---
def procesar_nota_ia(img_bytes):
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        img = Image.open(io.BytesIO(img_bytes))
        prompt = "Lee la nota de entrega. Devuelve SOLO un JSON: {'nombre':'', 'tel':'', 'dir':''}"
        response = model.generate_content([prompt, img])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except Exception as e:
        st.error(f"Error en IA: {e}")
        return None

# --- MANEJADORES DEL BOT ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔍 Tropiexpress: Procesando imagen...")
    
    # Descargar foto
    file = await update.message.photo[-1].get_file()
    fb = await file.download_as_bytearray()
    
    # Procesar en hilo aparte para evitar el bucle infinito
    loop = asyncio.get_event_loop()
    datos = await loop.run_in_executor(None, procesar_nota_ia, fb)
    
    if datos:
        # Limpiar número
        datos['tel'] = ''.join(filter(str.isdigit, str(datos.get('tel', ''))))
        st.session_state.temp_datos = datos
        await msg.edit_text(f"✅ ¡Nota leída! Revisa la App para confirmar a: {datos['nombre']}")
    else:
        await msg.edit_text("❌ No pude leer la nota. Intenta una foto más cerca.")

# --- INTERFAZ STREAMLIT ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Validación de Registro")
    if st.session_state.temp_datos:
        with st.form("validador"):
            nom = st.text_input("Nombre", st.session_state.temp_datos['nombre'])
            tel = st.text_input("Teléfono", st.session_state.temp_datos['tel'])
            dir = st.text_input("Dirección", st.session_state.temp_datos['dir'])
            
            if st.form_submit_button("Confirmar y Guardar"):
                if tel in st.session_state.db_clientes["Telefono"].values:
                    st.warning("Ese cliente ya existe.")
                else:
                    nuevo = {"Nombre": nom, "Telefono": tel, "Direccion": dir}
                    # Enviar a Sheets
                    requests.post(st.secrets["SHEETS_URL"], json=nuevo, timeout=10)
                    # Guardar local
                    st.session_state.db_clientes = pd.concat([st.session_state.db_clientes, pd.DataFrame([nuevo])], ignore_index=True)
                    st.success(f"Bienvenido {nom} a Tropiexpress")
                    st.code(f"¡Hola {nom}! 👋 Ya registramos tu dirección: {dir}")
                    st.session_state.temp_datos = None
    else:
        st.info("Esperando que envíes una nota por Telegram...")

with col2:
    st.subheader("📊 Historial Reciente")
    st.dataframe(st.session_state.db_clientes, use_container_width=True)

# --- ARRANQUE SEGURO ---
def run_bot():
    # Loop interno para evitar el RuntimeError de tu captura
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = Application.builder().token(st.secrets["TELEGRAM_TOKEN"]).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling(drop_pending_updates=True, close_loop=False)

if "bot_running" not in st.session_state:
    threading.Thread(target=run_bot, daemon=True).start()
    st.session_state.bot_running = True
