import streamlit as st
import pandas as pd
import json, re, requests, io, threading, asyncio
from PIL import Image
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress Ultra", layout="wide")
st.title("🚛 Tropiexpress: Gestión de Clientes Pro")

# Inicializar estados de memoria
if "db_clientes" not in st.session_state:
    st.session_state.db_clientes = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion", "Estado"])
if "temp_datos" not in st.session_state:
    st.session_state.temp_datos = None

# --- NÚCLEO DE INTELIGENCIA ARTIFICIAL ---
def extraer_datos_ia(image_bytes):
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        img = Image.open(io.BytesIO(image_bytes))
        prompt = "Lee la nota y entrega SOLO un JSON: {'nombre':'', 'tel':'', 'dir':''}"
        response = model.generate_content([prompt, img])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except Exception as e:
        print(f"Error IA: {e}")
        return None

# --- FUNCIONES DEL BOT (TELEGRAM) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Si es FOTO
    if update.message.photo:
        await update.message.reply_text("🔍 Leyendo nota de Tropiexpress...")
        file = await update.message.photo[-1].get_file()
        fb = await file.download_as_bytearray()
        datos = extraer_datos_ia(fb)
        if datos:
            datos['tel'] = ''.join(filter(str.isdigit, str(datos.get('tel', ''))))
            st.session_state.temp_datos = datos
            await update.message.reply_text(f"✅ ¡Leído! Revisa la App para confirmar a: {datos['nombre']}")
        else:
            await update.message.reply_text("❌ No pude leer la nota. Intenta dictar por audio.")
    
    # Si es AUDIO (Respaldo)
    elif update.message.voice or update.message.audio:
        await update.message.reply_text("🎤 Audio recibido. Por favor, ingresa los datos manualmente en la App.")

# --- INTERFAZ DE CONTROL (STREAMLIT) ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Revisar y Editar Registro")
    if st.session_state.temp_datos:
        with st.form("form_registro"):
            n = st.text_input("Nombre", st.session_state.temp_datos['nombre'])
            t = st.text_input("Teléfono", st.session_state.temp_datos['tel'])
            d = st.text_input("Dirección", st.session_state.temp_datos['dir'])
            
            if st.form_submit_button("Guardar Cliente"):
                # 1. No repetir clientes (Control de duplicados)
                if t in st.session_state.db_clientes["Telefono"].values:
                    st.error("⚠️ Este cliente ya existe en la base de datos.")
                else:
                    nuevo = {"Nombre": n, "Telefono": t, "Direccion": d, "Estado": "Registrado"}
                    # 2. Enviar a Google Sheets
                    try:
                        requests.post(st.secrets["SHEETS_URL"], json=nuevo, timeout=5)
                    except: pass
                    
                    # 3. Guardar en historial local
                    st.session_state.db_clientes = pd.concat([st.session_state.db_clientes, pd.DataFrame([nuevo])], ignore_index=True)
                    st.success(f"✅ Cliente {n} guardado correctamente.")
                    
                    # 4. Mensaje de bienvenida (para copiar y enviar)
                    st.info("*Mensaje de Bienvenida:*")
                    st.code(f"¡Hola {n}! 👋 Bienvenido a Tropiexpress. Hemos registrado tu dirección: {d}. ¡Es un gusto atenderte!")
                    st.session_state.temp_datos = None
    else:
        st.write("Esperando datos desde Telegram...")

with col2:
    st.subheader("📋 Registro de Hoy")
    st.dataframe(st.session_state.db_clientes, use_container_width=True)

# --- INICIO DEL SERVIDOR ---
def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = Application.builder().token(st.secrets["TELEGRAM_TOKEN"]).build()
    app.add_handler(MessageHandler(filters.PHOTO | filters.VOICE | filters.AUDIO, handle_message))
    app.run_polling(drop_pending_updates=True, close_loop=False)

if "bot_started" not in st.session_state:
    threading.Thread(target=start_bot, daemon=True).start()
    st.session_state.bot_started = True
