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
# Estos son los nombres exactos y vigentes en el panel de Groq
MODELOS_VISION_DISPONIBLES = [
    "llama-3.2-11b-vision-instant", 
    "llama-3.2-90b-vision-instant"
]
MODELO_VOZ = "whisper-large-v3-turbo"

try:
    API_KEY = st.secrets["GROQ_API_KEY"]
except:
    API_KEY = ""

client = Groq(api_key=API_KEY)

st.set_page_config(page_title="Tropiexpress Ultra-AI", page_icon="🛒", layout="wide")

if 'db_clientes' not in st.session_state:
    st.session_state['db_clientes'] = []

# --- 2. FUNCIONES IA ---

def transcribir_audio(audio_bytes):
    try:
        file_tuple = ("audio.wav", audio_bytes, "audio/wav")
        transcription = client.audio.transcriptions.create(
            file=file_tuple,
            model=MODELO_VOZ,
            language="es"
        )
        return transcription.text
    except Exception as e:
        st.error(f"Error en voz: {e}")
        return ""

def analizar_con_groq(imagen_bytes):
    base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
    
    # Intentamos con los modelos disponibles
    for modelo in MODELOS_VISION_DISPONIBLES:
        try:
            completion = client.chat.completions.create(
                model=modelo,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extrae de la nota: nombre, tel, dir. Responde solo JSON: {'nombre': '...', 'tel': '...', 'dir': '...'}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }],
                response_format={"type": "json_object"}
            )
            res = json.loads(completion.choices[0].message.content)
            if res.get('tel'):
                res['tel'] = re.sub(r'\D', '', str(res['tel']))
            return res
        except Exception as e:
            # Si falla un modelo, probamos el siguiente sin detener la app
            continue
    
    return None

# --- 3. INTERFAZ ---
st.title("🛒 Tropiexpress Ultra-Extract v3.1")

archivo = st.file_uploader("📸 Sube la nota", type=['jpg', 'jpeg', 'png'])
col1, col2 = st.columns(2)

if archivo:
    bytes_data = archivo.getvalue()
    with col1:
        st.image(bytes_data, use_container_width=True)
        if st.button("🚀 PROCESAR IMAGEN", use_container_width=True):
            with st.spinner("Conectando con la IA de Tropiexpress..."):
                res = analizar_con_groq(bytes_data)
                if res:
                    st.session_state['temp_datos'] = res
                    tel_nuevo = res.get('tel', '')
                    if any(c['Tel'] == tel_nuevo for c in st.session_state['db_clientes']):
                        st.warning(f"⚠️ El teléfono {tel_nuevo} ya está en tu lista.")
                    else:
                        st.success("✅ Datos extraídos correctamente.")
                else:
                    st.error("❌ Los modelos de Groq no responden. Verifica tu API KEY o el saldo de Groq.")

    with col2:
        st.subheader("📝 Confirmación de Datos")
        datos = st.session_state.get('temp_datos', {'nombre': '', 'tel': '', 'dir': ''})
        
        # Micro para corrección
        audio_dictado = mic_recorder(start_prompt="Dictar 🎙️", stop_prompt="Parar ⏹️", key='dictador')
        if audio_dictado:
            texto = transcribir_audio(audio_dictado['bytes'])
            if texto: st.info(f"Escuché: {texto}")

        with st.form("registro"):
            nom = st.text_input("Nombre", value=datos.get('nombre', ''))
            tel = st.text_input("Teléfono", value=datos.get('tel', ''))
            dire = st.text_input("Dirección", value=datos.get('dir', ''))
            promo = st.selectbox("Estrategia", ["Envío Gratis 🚚", "Bono $5.000 🎁", "Cliente Frecuente ⭐"])
            
            if st.form_submit_button("✅ GUARDAR Y WHATSAPP"):
                st.session_state['db_clientes'].append({
                    "Fecha": datetime.now().strftime("%d/%m %H:%M"),
                    "Cliente": nom, "Tel": tel, "Dir": dire, "Promo": promo
                })
                wa_num = f"57{tel}" if len(tel) == 10 else tel
                msg = f"Hola {nom} 🛒, Tropiexpress confirma tu pedido.\n📍 Dirección: {dire}\n🎁 Regalo: {promo}"
                link = f"https://wa.me/{wa_num}?text={urllib.parse.quote(msg)}"
                st.markdown(f'<a href="{link}" target="_blank"><div style="background-color:#25D366;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">📲 ENVIAR WHATSAPP</div></a>', unsafe_allow_html=True)

# --- TABLA ---
if st.session_state['db_clientes']:
    st.divider()
    df = pd.DataFrame(st.session_state['db_clientes'])
    st.dataframe(df.iloc[::-1], use_container_width=True)
