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

# Título en la web de Streamlit
st.set_page_config(page_title="Tropiexpress Server", page_icon="🚛")
st.title("🚛 Servidor Tropiexpress Activo")

# --- LÓGICA DE EXTRACCIÓN MEJORADA ---
def extraer_datos_ia(image_bytes):
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        # Usamos configuraciones para saltar bloqueos de seguridad por datos personales
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            generation_config={"temperature": 0.1},
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        )
        
        img = Image.open(io.BytesIO(image_bytes))
        prompt = "Lee la nota y entrega SOLO un JSON con llaves: nombre, tel, dir. Si no ves algo, pon 'S/D'."
        
        response = model.generate_content([prompt, img])
        
        # Limpieza del texto recibido
        texto_limpio = re.search(r'\{.*\}', response.text, re.DOTALL)
        if texto_limpio:
            return json.loads(texto_limpio.group(0))
        return None
    except Exception as e:
        st.error(f"Error técnico en IA: {e}")
        return None

# --- FUNCIONES DEL BOT ---
async def procesar_nota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔍 Tropiexpress: Leyendo nota...")
    
    file = await update.message.photo[-1].get_file()
    foto_bytes = await file.download_as_bytearray()
    
    datos = extraer_datos_ia(foto_bytes)
    
    if datos:
        # Limpiar el teléfono para que solo queden números
        datos['tel'] = ''.join(filter(str.isdigit, str(datos.get('tel', ''))))
        context.user_data['datos'] = datos
        
        resumen = (
            f"✅ *Nota Leída:*\n\n"
            f"👤 *Cliente:* {datos.get('nombre')}\n"
            f"📞 *Tel:* {datos.get('tel')}\n"
            f"📍 *Dir:* {datos.get('dir')}\n\n"
            "¿Guardar? (Responde *SI*)"
        )
        await msg.edit_text(resumen, parse_mode=constants.ParseMode.MARKDOWN)
        return 1
    
    await msg.edit_text("❌ No logré extraer los datos. Intenta con otra foto.")
    return ConversationHandler.END

async def guardar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "SI" in update.message.text.upper():
        try:
            requests.post(st.secrets["SHEETS_URL"], json=context.user_data['datos'], timeout=10)
            await update.message.reply_text("💾 ¡Guardado en tu Excel de Tropiexpress!")
        except:
            await update.message.reply_text("❌ Error al enviar a Google Sheets.")
    return ConversationHandler.END

# --- ARRANQUE DEL SERVIDOR ---
if st.button("🚀 Iniciar/Reiniciar Bot"):
    st.info("Iniciando conexión con Telegram...")
    
    # Configuración de la App de Telegram
    app = Application.builder().token(st.secrets["TELEGRAM_TOKEN"]).build()
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, procesar_nota)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, guardar)]},
        fallbacks=[]
    )
    
    app.add_handler(conv_handler)
    
    # Ejecución asíncrona para evitar el RuntimeError de la imagen anterior
    async def run_bot():
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        st.success("✅ ¡Bot en línea! Envía una foto por Telegram.")
        while True: await asyncio.sleep(3600)

    asyncio.run(run_bot())
