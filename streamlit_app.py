import streamlit as st
import io
import re
import json
import requests
import logging
from PIL import Image
import google.generativeai as genai
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Configuración de IA con la llave de los Secrets
genai.configure(api_key=st.secrets["GEMINI_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

CONFIRMACION = 1

async def procesar_nota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = await update.message.reply_text("🚛 *Tropiexpress:* Analizando nota...")
    
    try:
        # Descarga la foto directamente al servidor
        file = await update.message.photo[-1].get_file()
        foto_bytes = await file.download_as_bytearray()
        img = Image.open(io.BytesIO(foto_bytes))
        
        # Prompt optimizado para evitar bloqueos de seguridad
        prompt = "Extrae Nombre, Teléfono y Dirección de esta nota. Responde solo con JSON: {'nombre':'', 'tel':'', 'dir':''}"
        response = model.generate_content([prompt, img])
        
        datos = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group(0))
        datos['tel'] = ''.join(filter(str.isdigit, str(datos['tel'])))
        context.user_data['datos'] = datos
        
        resumen = (
            f"✅ *¡Nota leída!\n\n👤 **Cliente:* {datos['nombre']}\n"
            f"📞 *Tel:* {datos['tel']}\n📍 *Dir:* {datos['dir']}\n\n"
            "¿Guardar datos? (Responde *SI*)"
        )
        await status.edit_text(resumen, parse_mode=constants.ParseMode.MARKDOWN)
        return CONFIRMACION
    except:
        await status.edit_text("⚠️ Error al leer. Intenta una foto más clara.")
        return ConversationHandler.END

async def guardar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "SI" in update.message.text.upper():
        requests.post(st.secrets["SHEETS_URL"], json=context.user_data['datos'])
        await update.message.reply_text("💾 Guardado en la base de datos.")
    return ConversationHandler.END

# Interfaz de Streamlit
st.title("Servidor Tropiexpress")
if st.button("Iniciar Bot"):
    app = Application.builder().token(st.secrets["TELEGRAM_TOKEN"]).build()
    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, procesar_nota)],
        states={CONFIRMACION: [MessageHandler(filters.TEXT, guardar)]},
        fallbacks=[]
    ))
    st.success("Bot activo en Telegram")
    app.run_polling()
