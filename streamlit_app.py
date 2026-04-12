import streamlit as st
from groq import Groq
import json
import urllib.parse
import re
import pandas as pd
import base64
from datetime import datetime
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIGURACIÓN ---
# Usamos ÚNICAMENTE el modelo de producción para evitar el Error 400
MODELO_VISION = "llama-3.2-11b-vision-instant"
MODELO_VOZ = "whisper-large-v3-turbo"

try:
    API_KEY = st.secrets["GROQ_API_KEY"]
except:
    API_KEY = ""

client = Groq(api_key=API_KEY)

st.set_page_config(page_title="Tropiexpress AI", page_icon="🛒", layout="wide")

# Inicializamos el estado de los datos si no existe
if 'temp_datos' not in st.session_state:
    st.session_state['temp_datos'] = {'nombre': '', 'tel': '', 'dir': ''}
if 'db_clientes' not in st.session_state:
    st.session_state['db_clientes'] = []

# --- 2. FUNCIONES IA ---

def transcribir_y_repartir(audio_bytes):
    """Toma el audio, lo vuelve texto y le pide a la IA que separe los campos"""
    try:
        file_tuple = ("audio.wav", audio_bytes, "audio/wav")
        transcription = client.audio.transcriptions.create(
            file=file_tuple,
            model=MODELO_VOZ,
            language="es"
        )
        texto = transcription.text
        
        # Le pedimos a la IA que organice el texto dictado en el formato JSON
        prompt = f"Del siguiente texto dictado, extrae nombre, teléfono y dirección. Responde SOLO JSON: {texto}"
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192", # Modelo rápido para texto
            response_format={"type": "json_object"}
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        st.error(f"Error procesando voz: {e}")
        return None

def analizar_imagen(imagen_bytes):
    """Extrae datos de la foto usando el modelo instant (Evita Error 400)"""
    base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
    try:
        completion = client.chat.completions.create(
            model=MODELO_VISION, # <--- Aquí estaba el error, ahora es 'instant'
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extrae: nombre, tel, dir. Responde JSON."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        st.error(f"Error de visión: {e}")
        return None

# --- 3. INTERFAZ ---
st.title("🛒 Tropiexpress Ultra-Extract v3.5")

archivo = st.file_uploader("📸 Sube la nota", type=['jpg', 'jpeg', 'png'])
col1, col2 = st.columns(2)

if archivo:
    bytes_data = archivo.getvalue()
    with col1:
        st.image(bytes_data, use_container_width=True)
        if st.button("🚀 PROCESAR IMAGEN", use_container_width=True):
            res = analizar_imagen(bytes_data)
            if res:
                st.session_state['temp_datos'] = {
                    'nombre': res.get('nombre', ''),
                    'tel': re.sub(r'\D', '', str(res.get('tel', ''))),
                    'dir': res.get('dir', '')
                }
                st.success("Imagen procesada. Revisa los campos.")

    with col2:
        st.subheader("📝 Confirmar Datos")
        
        # --- SECCIÓN DE VOZ ---
        st.write("🎙️ *Dictar datos completos:*")
        audio = mic_recorder(start_prompt="Hablar 🎙️", stop_prompt="Parar ⏹️", key='voz_repartir')
        
        if audio:
            with st.spinner("Repartiendo datos en los campos..."):
                datos_voz = transcribir_y_repartir(audio['bytes'])
                if datos_voz:
                    # Actualizamos el estado para que los inputs se llenen solos
                    st.session_state['temp_datos'] = {
                        'nombre': datos_voz.get('nombre', ''),
                        'tel': re.sub(r'\D', '', str(datos_voz.get('tel', ''))),
                        'dir': datos_voz.get('dir', '')
                    }
                    st.rerun() # Refresca para mostrar los datos en los cuadros

        # --- FORMULARIO CON AUTO-LLENADO ---
        with st.form("registro"):
            # Usamos session_state para que el valor cambie dinámicamente
            nom = st.text_input("Nombre", value=st.session_state['temp_datos']['nombre'])
            tel = st.text_input("WhatsApp", value=st.session_state['temp_datos']['tel'])
            dire = st.text_input("Dirección", value=st.session_state['temp_datos']['dir'])
            promo = st.selectbox("Estrategia", ["Envío Gratis 🚚", "Bono $5.000 🎁", "Cliente Frecuente ⭐"])
            
            if st.form_submit_button("✅ GUARDAR Y WHATSAPP"):
                # Detección de duplicados antes de guardar
                if any(c['Tel'] == tel for c in st.session_state['db_clientes']):
                    st.warning("⚠️ Este cliente ya fue registrado.")
                else:
                    st.session_state['db_clientes'].append({
                        "Fecha": datetime.now().strftime("%d/%m %H:%M"),
                        "Cliente": nom, "Tel": tel, "Dir": dire, "Promo": promo
                    })
                    wa_num = f"57{tel}" if len(tel) == 10 else tel
                    msg = f"Hola {nom} 🛒, Tropiexpress confirma tu pedido.\n📍 Dirección: {dire}\n🎁 Regalo: {promo}"
                    link = f"https://wa.me/{wa_num}?text={urllib.parse.quote(msg)}"
                    st.markdown(f'<a href="{link}" target="_blank"><div style="background-color:#25D366;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">📲 ENVIAR BIENVENIDA</div></a>', unsafe_allow_html=True)

# --- TABLA ---
if st.session_state['db_clientes']:
    st.divider()
    df = pd.DataFrame(st.session_state['db_clientes'])
    st.dataframe(df.iloc[::-1], use_container_width=True)
