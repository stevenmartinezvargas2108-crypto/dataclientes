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
# Usamos el modelo 'instant' que es el más estable para las llamadas que ya activaste
MODELO_VISION = "llama-3.2-11b-vision-instant"
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
        return ""

def analizar_con_groq(imagen_bytes):
    base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
    try:
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
        st.error(f"Error técnico: {e}")
        return None

# --- 3. INTERFAZ ---
st.title("🛒 Tropiexpress Ultra-Extract")

archivo = st.file_uploader("📸 Sube la nota", type=['jpg', 'jpeg', 'png'])
col1, col2 = st.columns(2)

if archivo:
    bytes_data = archivo.getvalue()
    with col1:
        st.image(bytes_data, use_container_width=True)
        if st.button("🚀 PROCESAR IMAGEN", use_container_width=True):
            with st.spinner("Leyendo nota..."):
                res = analizar_con_groq(bytes_data)
                if res:
                    st.session_state['temp_datos'] = res
                    tel_nuevo = res.get('tel', '')
                    # Detección de duplicados
                    if any(c['Tel'] == tel_nuevo for c in st.session_state['db_clientes']):
                        st.warning(f"⚠️ El cliente con tel {tel_nuevo} ya ha sido registrado hoy.")
                    else:
                        st.success("✅ Datos extraídos.")

    with col2:
        st.subheader("📝 Confirmar Datos")
        datos = st.session_state.get('temp_datos', {'nombre': '', 'tel': '', 'dir': ''})
        
        # Micro para corrección por voz
        audio_dictado = mic_recorder(start_prompt="Dictar corrección 🎙️", stop_prompt="Parar ⏹️", key='dictador')
        if audio_dictado:
            texto = transcribir_audio(audio_dictado['bytes'])
            if texto: st.info(f"Escuché: {texto}")

        with st.form("registro"):
            nom = st.text_input("Nombre", value=datos.get('nombre', ''))
            tel = st.text_input("WhatsApp", value=datos.get('tel', ''))
            dire = st.text_input("Dirección", value=datos.get('dir', ''))
            promo = st.selectbox("Estrategia", ["Envío Gratis 🚚", "Bono $5.000 🎁", "Cliente Frecuente ⭐"])
            
            if st.form_submit_button("✅ GUARDAR Y WHATSAPP"):
                st.session_state['db_clientes'].append({
                    "Fecha": datetime.now().strftime("%d/%m %H:%M"),
                    "Cliente": nom, "Tel": tel, "Dir": dire, "Promo": promo
                })
                # Generar link de WhatsApp
                wa_num = f"57{tel}" if len(tel) == 10 else tel
                msg = f"Hola {nom} 🛒, Tropiexpress confirma tu pedido.\n📍 Dirección: {dire}\n🎁 Regalo: {promo}"
                link = f"https://wa.me/{wa_num}?text={urllib.parse.quote(msg)}"
                st.markdown(f'<a href="{link}" target="_blank"><div style="background-color:#25D366;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">📲 ENVIAR BIENVENIDA</div></a>', unsafe_allow_html=True)

# --- 4. TABLA ---
if st.session_state['db_clientes']:
    st.divider()
    df = pd.DataFrame(st.session_state['db_clientes'])
    st.dataframe(df.iloc[::-1], use_container_width=True)
    
    # Exportar a Excel
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 Descargar Excel", output.getvalue(), "pedidos_tropiexpress.xlsx")
