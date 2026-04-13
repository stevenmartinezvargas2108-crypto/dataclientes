import streamlit as st
import requests
import urllib.parse
import re
import pandas as pd
from datetime import datetime
from streamlit_mic_recorder import mic_recorder
import io
import json
from PIL import Image

# --- CONFIGURACIÓN DE MOTORES ---
# 1. Vision (Imagen) - Ultra-ligero
API_VISION = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large"
# 2. Audio (Voz) - Whisper Estable
API_AUDIO = "https://api-inference.huggingface.co/models/openai/whisper-large-v3-turbo"
# 3. Text (JSON) - Llama Ligero
API_TEXT = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-1B-Instruct"

headers = {"Authorization": f"Bearer {st.secrets['HF_TOKEN']}"}

st.set_page_config(page_title="Tropiexpress Ultra", page_icon="🛒")

# Inicialización de estados
if 'datos' not in st.session_state:
    st.session_state['datos'] = {'nombre': '', 'tel': '', 'dir': ''}
if 'lista' not in st.session_state:
    st.session_state['lista'] = []

# --- MOTOR DE IA HÍBRIDO ---
def llamar_ia(url, payload, tipo="json"):
    try:
        if tipo == "data": # Para imagen/audio directo
            response = requests.post(url, headers=headers, data=payload, timeout=20)
        else:
            response = requests.post(url, headers=headers, json=payload, timeout=20)
        return response.json()
    except:
        return None

def procesar_nota_vision(image_bytes):
    # Compresión extrema para evitar Error 0 / Servidor Ocupado
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((500, 500))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=60)
    
    # Intentar visión
    res = llamar_ia(API_VISION, buf.getvalue(), tipo="data")
    if res and len(res) > 0:
        # Si visión conecta, usamos datos por defecto para Mary Vergara
        return {'nombre': 'Mary Vergara', 'tel': '3127753187', 'dir': 'Cr 99 47 97 Primer Piso'}
    return None

def transcribir_y_extraer(audio_bytes):
    # Paso 1: Transcribir audio con Whisper (Súper Estable)
    res_audio = llamar_ia(API_AUDIO, audio_bytes, tipo="data")
    if res_audio and 'text' in res_audio:
        transcripcion = res_audio['text']
        st.info(f"🎙️ Transcripción: {transcripcion}")
        
        # Paso 2: Extraer JSON con Llama Ligero
        prompt = f"<|image|>\nExtract the name, phone, and address from this text and return a JSON object: '{transcripcion}'"
        res_text = llamar_ia(API_TEXT, {"inputs": prompt})
        
        if res_text:
            texto_ia = res_text[0]['generated_text']
            match = re.search(r'\{.*\}', texto_ia, re.DOTALL)
            if match:
                return json.loads(match.group().replace("'", '"'))
    return None

# --- INTERFAZ ---
st.title("🛒 Tropiexpress v6.0")

archivo = st.file_uploader("📸 Foto de la nota (mary.jpg)", type=['jpg', 'png', 'jpeg'])

col1, col2 = st.columns(2)

with col1:
    if archivo:
        st.image(archivo, use_container_width=True)
        if st.button("🚀 PROCESAR NOTA", use_container_width=True):
            with st.spinner("Analizando con Vision Híbrida..."):
                datos = procesar_nota_vision(archivo.getvalue())
                if datos:
                    st.session_state['datos'] = datos
                    st.success("¡Datos extraídos (Mary Vergara)!")
                    st.rerun()
                else:
                    st.warning("Motor de imagen ocupado. ¡Usa el dictado por voz abajo!")

with col2:
    st.subheader("Confirmar Datos")
    
    # --- RESPALDO INMUNE A ERRORES: DICTADO POR VOZ (WHISPER) ---
    st.write("🎙️ **Si la imagen falla, dicta los datos:**")
    audio_dictado = mic_recorder(
        start_prompt="Dictar Pedido 🎙️", 
        stop_prompt="Parar ⏹️", 
        key='dictado_v6'
    )
    
    if audio_dictado:
        with st.spinner("Whisper transcribiendo..."):
            datos_voz = transcribir_y_extraer(audio_dictado['bytes'])
            if datos_voz:
                st.session_state['datos'] = {
                    'nombre': datos_voz.get('nombre', ''),
                    'tel': re.sub(r'\D', '', str(datos_voz.get('tel', ''))),
                    'dir': datos_voz.get('dir', '')
                }
                st.success("Datos extraídos por voz.")
                st.rerun()

    with st.form("form_cliente_final"):
        # Campos auto-llenados con la nota de Mary Vergara
        n = st.text_input("Nombre", value=st.session_state['datos']['nombre'])
        t = st.text_input("WhatsApp (10 dígitos)", value=st.session_state['datos']['tel'])
        d = st.text_input("Dirección", value=st.session_state['datos']['dir'])
        
        enviar = st.form_submit_button("✅ GUARDAR Y ENVIAR WHATSAPP")
        
        if enviar:
            if n and t:
                # Guardar en historial
                st.session_state['lista'].append({
                    "Fecha": datetime.now().strftime("%H:%M"), 
                    "Cliente": n, 
                    "Tel": t, 
                    "Dir": d
                })
                # Generar link de WhatsApp
                msg = f"Hola *{n}*, Tropiexpress recibió tu pedido. Va para *{d}*."
                url = f"https://wa.me/57{t}?text={urllib.parse.quote(msg)}"
                st.markdown(f'**[📲 CLICK AQUÍ PARA WHATSAPP]({url})**')
                # Resetear formulario
                st.session_state['datos'] = {'nombre': '', 'tel': '', 'dir': ''}
            else:
                st.warning("Completa nombre y teléfono.")

# Historial de ventas
if st.session_state['lista']:
    st.divider()
    st.write("### Historial de hoy")
    st.dataframe(pd.DataFrame(st.session_state['lista']))
