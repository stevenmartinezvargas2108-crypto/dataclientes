import streamlit as st
import threading
import io
import re
import json
import requests
import asyncio
from PIL import Image
import google.generativeai as genai
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress Server", page_icon="🚛")
st.title("🚛 Tropiexpress: Servidor Activo")

# --- MOTOR DE INTELIGENCIA ARTIFICIAL ---
def extraer_datos_ia(image_bytes):
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        # Configuración agresiva para evitar bloqueos por "seguridad"
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        )
        img = Image.open(io.BytesIO(image_bytes))
        prompt = "Extrae Nombre, Tel y Dirección. Responde SOLO JSON: {'nombre':'', 'tel':'', 'dir':''}"
        response = model.generate_content([prompt, img])
        
        texto_limpio = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(texto_limpio.group(0)) if texto_limpio else None
    except Exception as e:
        print(f"Error en Gemini: {e}")
        return None

# --- MANEJADORES DE TELEGRAM ---
async def procesar_nota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usamos respuesta inmediata para evitar que Telegram piense que el bot murió
    msg = await update.message.reply_text("🚛 Tropiexpress está leyendo la nota...")
    
    try:
        file = await update.message.photo[-1].get_file()
        foto_bytes = await file.download_as_bytearray()
        
        # Procesar en un ejecutor para no bloquear el bucle de eventos
        loop = asyncio.get_event_loop()
        datos = await loop.run_in_executor(None, extraer_datos_ia, foto_bytes)
        
        if datos:
            datos['tel'] = ''.join(filter(str.isdigit, str(datos.get('tel', ''))))
            context.user_data['datos'] = datos
            resumen = (
                f"✅ *¡Nota procesada!*\n\n"
                f"👤 *Cliente:* {datos.get('nombre')}\n"
                f"📞 *Tel:* {datos.get('tel')}\n"
                f"📍 *Dir:* {datos.get('dir')}\n\n"
                "¿Deseas guardar? (Responde *SI*)"
            )
            await msg.edit_text(resumen, parse_mode=constants.ParseMode.MARKDOWN)
            return 1
        else:
            await msg.edit_text("⚠️ No pude leer los datos. Asegúrate de que la foto no tenga sombras.")
    except Exception as e:
        await msg.edit_text(f"❌ Error de procesamiento: {str(e)}")
    return ConversationHandler.END

async def guardar_datos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "SI" in update.message.text.upper():
        d = context.user_data['datos']
        requests.post(st.secrets["SHEETS_URL"], json=d, timeout=10)
        await update.message.reply_text("💾 Guardado en tu base de datos.")
    return ConversationHandler.END

# --- INICIALIZADOR DEL BOT ---
def run_telegram_bot():
    # Creamos un nuevo bucle de eventos para este hilo
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    app = Application.builder().token(st.secrets["TELEGRAM_TOKEN"]).build()
    
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, procesar_nota)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_datos)]},
        fallbacks=[CommandHandler('start', lambda u,c: u.message.reply_text("Listo"))]
    ))
    
    st.write("🤖 Bot escuchando mensajes...")
    app.run_polling(drop_pending_updates=True, close_loop=False)

# Evitar que Streamlit cree múltiples hilos al recargar
if "bot_thread" not in st.session_state:
    thread = threading.Thread(target=run_telegram_bot, daemon=True)
    thread.start()
    st.session_state["bot_thread"] = True

st.success("✅ El sistema está en línea. Puedes cerrar esta pestaña y el bot seguirá trabajando.")
