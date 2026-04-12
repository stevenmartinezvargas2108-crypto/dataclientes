import streamlit as st
from groq import Groq
import json
import urllib.parse
import re
import pandas as pd
import base64
from datetime import datetime
from streamlit_mic_recorder import mic_recorder # Nueva librería para voz

# --- CONFIGURACIÓN ---
API_KEY = st.secrets.get("GROQ_API_KEY", "")
client = Groq(api_key=API_KEY)

MODELO_VISION = "llama-3.2-90b-vision-preview" 
MODELO_VOZ = "whisper-large-v3-turbo" # El mejor para dictado

st.set_page_config(page_title="Tropiexpress Ultra-AI", page_icon="🛒", layout="wide")

if 'db_clientes' not in st.session_state:
    st.session_state['db_clientes'] = []

# --- FUNCIONES ---
def transcribir_audio(audio_bytes):
    try:
        # Groq requiere un nombre de archivo para procesar el buffer
        file_tuple = ("audio.wav", audio_bytes, "audio/wav")
        transcription = client.audio.transcriptions.create(
            file=file_tuple,
            model=MODELO_VOZ,
            language="es"
        )
        return transcription.text
    except Exception as e:
        st.error(f"Error al procesar voz: {e}")
        return ""

def analizar_con_groq(imagen_bytes):
    try:
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        completion = client.chat.completions.create(
            model=MODELO_VISION,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extrae: nombre, tel, dir. Responde solo JSON: {'nombre': '...', 'tel': '...', 'dir': '...'}"},
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
        st.error(f"Error con la cámara: {e}")
        return None

# --- INTERFAZ ---
st.title("🛒 Tropiexpress Ultra-Extract + Voz")

archivo = st.file_uploader("📸 Sube la nota", type=['jpg', 'jpeg', 'png'])
col1, col2 = st.columns(2)

if archivo:
    bytes_data = archivo.getvalue()
    with col1:
        st.image(bytes_data, caption="Nota original", use_container_width=True)
        if st.button("🚀 PROCESAR IMAGEN"):
            res = analizar_con_groq(bytes_data)
            if res:
                st.session_state['temp_datos'] = res
                tel_nuevo = res.get('tel', '')
                if any(c['Tel'] == tel_nuevo for c in st.session_state['db_clientes']):
                    st.warning(f"⚠️ ¡Cliente repetido! Tel: {tel_nuevo}")
                else:
                    st.success("✅ Cliente nuevo.")

    with col2:
        st.subheader("📝 Datos del Cliente")
        datos = st.session_state.get('temp_datos', {'nombre': '', 'tel': '', 'dir': ''})
        
        # --- SECCIÓN DE DICTADO ---
        st.info("🎙️ ¿Necesitas corregir algo? Pulsa el micro y habla.")
        audio_dictado = mic_recorder(start_prompt="Record 🎙️", stop_prompt="Stop ⏹️", key='dictador', just_once=True)
        
        if audio_dictado:
            texto_dictado = transcribir_audio(audio_dictado['bytes'])
            if texto_dictado:
                st.write(f"✍️ Escuché: {texto_dictado}")
                st.info("Copia y pega arriba si es necesario.")

        with st.form("registro"):
            nom = st.text_input("Nombre", value=datos.get('nombre', ''))
            tel = st.text_input("Teléfono", value=datos.get('tel', ''))
            dire = st.text_input("Dirección", value=datos.get('dir', ''))
            promo = st.selectbox("Promoción", ["Envío Gratis 🚚", "Bono $5.000 🎁", "Cliente Frecuente ⭐"])
            
            if st.form_submit_button("✅ GUARDAR Y WHATSAPP"):
                # Registro en la lista
                nuevo = {
                    "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Cliente": nom, "Tel": tel, "Dir": dire, "Promo": promo
                }
                st.session_state['db_clientes'].append(nuevo)
                
                # Link WhatsApp
                wa_num = f"57{tel}" if len(tel) == 10 else tel
                msg = f"Hola {nom} 🛒, Tropiexpress confirma tu pedido.\n📍 Dirección: {dire}\n🎁 Regalo: {promo}"
                link = f"https://wa.me/{wa_num}?text={urllib.parse.quote(msg)}"
                
                st.markdown(f'''
                    <a href="{link}" target="_blank">
                        <div style="background-color:#25D366;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">
                            📲 ENVIAR MENSAJE DE BIENVENIDA
                        </div>
                    </a>
                ''', unsafe_allow_html=True)

# --- TABLA Y EXPORTACIÓN ---
st.divider()
if st.session_state['db_clientes']:
    df = pd.DataFrame(st.session_state['db_clientes'])
    st.subheader("📋 Historial Tropiexpress")
    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Descargar Base de Datos", csv, "pedidos_tropiexpress.csv", "text/csv")
