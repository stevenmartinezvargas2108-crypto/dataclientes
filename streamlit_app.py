import streamlit as st
from groq import Groq
import json
import urllib.parse
import re
import pandas as pd
import base64
from datetime import datetime
from streamlit_mic_recorder import mic_recorder

# --- 1. MODELOS ACTUALIZADOS (Enero-Abril 2026) ---
# Cambiamos los modelos 'preview' por 'instant' para evitar el error 400
MODELO_VISION = "llama-3.2-11b-vision-instant" 
MODELO_TEXTO = "llama-3.3-70b-versatile" # Modelo nuevo y estable
MODELO_VOZ = "whisper-large-v3-turbo"

try:
    API_KEY = st.secrets["GROQ_API_KEY"]
except:
    API_KEY = ""

client = Groq(api_key=API_KEY)

st.set_page_config(page_title="Tropiexpress AI", page_icon="🛒", layout="wide")

# Mantener los datos vivos en la pantalla
if 'temp_datos' not in st.session_state:
    st.session_state['temp_datos'] = {'nombre': '', 'tel': '', 'dir': ''}
if 'db_clientes' not in st.session_state:
    st.session_state['db_clientes'] = []

# --- 2. FUNCIONES DE PROCESAMIENTO ---

def procesar_voz_a_campos(audio_bytes):
    """Transcribe y organiza los datos dictados en los campos"""
    try:
        file_tuple = ("audio.wav", audio_bytes, "audio/wav")
        transcription = client.audio.transcriptions.create(
            file=file_tuple,
            model=MODELO_VOZ,
            language="es"
        )
        texto_dictado = transcription.text
        
        # Le pedimos al nuevo modelo de texto que organice el dictado
        prompt = f"Extrae nombre, teléfono y dirección de este dictado: '{texto_dictado}'. Responde SOLO en formato JSON: {{'nombre': '...', 'tel': '...', 'dir': '...'}}"
        
        res_ia = client.chat.completions.create(
            model=MODELO_TEXTO,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(res_ia.choices[0].message.content)
    except Exception as e:
        st.error(f"Error en voz: {e}")
        return None

def analizar_imagen_fija(imagen_bytes):
    """Lee la imagen con el modelo de visión actualizado"""
    base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
    try:
        completion = client.chat.completions.create(
            model=MODELO_VISION,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extrae: nombre, tel, dir de la nota. Responde solo JSON."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        st.error(f"Error de visión (Modelo nuevo): {e}")
        return None

# --- 3. INTERFAZ ---
st.title("🛒 Tropiexpress Ultra-Extract v3.6")

archivo = st.file_uploader("📸 Sube la nota del cliente", type=['jpg', 'jpeg', 'png'])
col1, col2 = st.columns(2)

if archivo:
    bytes_data = archivo.getvalue()
    with col1:
        st.image(bytes_data, use_container_width=True)
        if st.button("🚀 PROCESAR IMAGEN", use_container_width=True):
            with st.spinner("Analizando foto..."):
                res = analizar_imagen_fija(bytes_data)
                if res:
                    st.session_state['temp_datos'] = {
                        'nombre': res.get('nombre', ''),
                        'tel': re.sub(r'\D', '', str(res.get('tel', ''))),
                        'dir': res.get('dir', '')
                    }
                    st.rerun()

    with col2:
        st.subheader("📝 Confirmar y Guardar")
        
        # BOTÓN DE DICTADO
        st.write("🎙️ *Dictar datos (Nombre, Tel, Dir):*")
        audio = mic_recorder(start_prompt="Hablar 🎙️", stop_prompt="Detener ⏹️", key='grabadora_v36')
        
        if audio:
            with st.spinner("Organizando datos dictados..."):
                datos_voz = procesar_voz_a_campos(audio['bytes'])
                if datos_voz:
                    st.session_state['temp_datos'] = {
                        'nombre': datos_voz.get('nombre', ''),
                        'tel': re.sub(r'\D', '', str(datos_voz.get('tel', ''))),
                        'dir': datos_voz.get('dir', '')
                    }
                    st.rerun()

        # FORMULARIO
        with st.form("registro_final"):
            nom = st.text_input("Nombre", value=st.session_state['temp_datos']['nombre'])
            tel = st.text_input("Teléfono / WhatsApp", value=st.session_state['temp_datos']['tel'])
            dire = st.text_input("Dirección", value=st.session_state['temp_datos']['dir'])
            promo = st.selectbox("Estrategia", ["Envío Gratis 🚚", "Bono $5.000 🎁", "Cliente Frecuente ⭐"])
            
            if st.form_submit_button("✅ GUARDAR Y GENERAR WHATSAPP"):
                st.session_state['db_clientes'].append({
                    "Fecha": datetime.now().strftime("%d/%m %H:%M"),
                    "Cliente": nom, "Tel": tel, "Dir": dire, "Promo": promo
                })
                # Link de WhatsApp
                wa_num = f"57{tel}" if len(tel) == 10 else tel
                msg = f"Hola {nom} 🛒, Tropiexpress confirma tu pedido.\n📍 Dirección: {dire}\n🎁 Regalo: {promo}"
                link = f"https://wa.me/{wa_num}?text={urllib.parse.quote(msg)}"
                st.markdown(f'<a href="{link}" target="_blank"><div style="background-color:#25D366;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;color:white;">📲 ENVIAR A WHATSAPP</div></a>', unsafe_allow_html=True)

# TABLA DE REGISTROS
if st.session_state['db_clientes']:
    st.divider()
    df = pd.DataFrame(st.session_state['db_clientes'])
    st.dataframe(df.iloc[::-1], use_container_width=True)
