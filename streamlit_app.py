import streamlit as st
import asyncio
import io
import re
import json
import requests
from PIL import Image
import google.generativeai as genai
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Configuración de página
st.set_page_config(page_title="Tropiexpress Server", page_icon="🚛")
st.title("🚛 Tropiexpress: Servidor Activo")

# --- LÓGICA DE IA ---
def extraer_datos_ia(image_bytes):
    genai.configure(api_key=st.secrets["GEMINI_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = "Extrae Nombre, Teléfono y Dirección de esta nota. Responde solo el JSON: {'nombre':'', 'tel':'', 'dir':''}"
    try:
        img = Image.open(io.BytesIO(image_bytes))
        response = model.generate_content([prompt, img])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except Exception as e:
        st.error(f"Error IA: {e}")
        return None

# --- MANEJADORES TELEGRAM ---
async def procesar_nota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = await update.message.reply_text("🔍 Leyendo nota...")
    photo = await update.message.photo[-1].get_file()
    foto_bytes = await photo.download_as_bytearray()
    
    datos = extraer_datos_ia(foto_bytes)
    if datos:
        datos['tel'] = ''.join(filter(str.isdigit, str(datos['tel'])))
        context.user_data['datos'] = datos
        resumen = f"✅ *Leído:*\n👤 {datos['nombre']}\n📞 {datos['tel']}\n📍 {datos['dir']}\n\n¿Guardar? (Escribe SI)"
        await status.edit_text(resumen, parse_mode=constants.ParseMode.MARKDOWN)
        return 1
    await status.edit_text("❌ No pude leerla. Intenta otra foto.")
    return ConversationHandler.END

async def guardar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "SI" in update.message.text.upper():
        requests.post(st.secrets["SHEETS_URL"], json=context.user_data['datos'], timeout=10)
        await update.message.reply_text("💾 Guardado en Spreadsheet.")
    return ConversationHandler.END

# --- LANZADOR DEL BOT (MODO NUBE) ---
async def iniciar_bot():
    app = Application.builder().token(st.secrets["TELEGRAM_TOKEN"]).build()
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, procesar_nota)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, guardar)]},
        fallbacks=[]
    ))
    
    # Esto evita el RuntimeError en la nube
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    st.success("✅ El bot ya está escuchando en Telegram.")
    
    # Mantiene el bot vivo sin bloquear a Streamlit
    while True:
        await asyncio.sleep(3600)

if st.button("🚀 Arrancar Bot"):
    try:
        asyncio.run(iniciar_bot())
    except Exception as e:
        st.error(f"Error de conexión: {e}")
