import streamlit as st
import google.generativeai as genai
import json
import urllib.parse
import re
import pandas as pd
from datetime import datetime
from streamlit_mic_recorder import mic_recorder
import io
from PIL import Image

# --- 1. CONFIGURACIÓN GEMINI ---
try:
    # Asegúrate de poner tu llave de Google en los Secrets de Streamlit
    GEMINI_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except:
    st.error("Falta la GOOGLE_API_KEY en los Secrets.")

# Configuramos los modelos de Google
# 'gemini-1.5-flash' es ultra rápido y excelente para leer fotos
model_vision = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Tropiexpress Gemini Edition", page_icon="🛒", layout="wide")

# Estado de la aplicación
if 'temp_datos' not in st.session_state:
    st.session_state['temp_datos'] = {'nombre': '', 'tel': '', 'dir': ''}
if 'db_clientes' not in st.session_state:
    st.session_state['db_clientes'] = []

# --- 2. FUNCIONES DE PROCESAMIENTO ---

def procesar_con_gemini(imagen_o_audio, es_imagen=True):
    """Función unificada para procesar datos con Gemini"""
    try:
        if es_imagen:
            # Procesar imagen de la nota
            img = Image.open(io.BytesIO(imagen_o_audio))
            prompt = "Actúa como un extractor de datos para un supermercado. Lee la nota y extrae NOMBRE, TELÉFONO y DIRECCIÓN. Responde estrictamente en formato JSON."
            response = model_vision.generate_content([prompt, img])
        else:
            # Procesar dictado por voz (Gemini acepta audio directamente)
            # Para audio usamos un prompt de texto sobre el archivo
            prompt = f"Del siguiente dictado, extrae nombre, teléfono y dirección: '{imagen_o_audio}'. Responde solo JSON."
            response = model_vision.generate_content(prompt)
        
        # Limpieza de la respuesta JSON
        texto_limpio = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(texto_limpio)
    except Exception as e:
        st.error(f"Error con Gemini: {e}")
        return None

# --- 3. INTERFAZ ---
st.title("🛒 Tropiexpress Gemini Ultra")

archivo = st.file_uploader("📸 Sube la nota (Mary Vergara...)", type=['jpg', 'jpeg', 'png'])
col1, col2 = st.columns(2)

if archivo:
    bytes_data = archivo.getvalue()
    with col1:
        st.image(bytes_data, use_container_width=True)
        if st.button("🚀 PROCESAR CON GEMINI", use_container_width=True):
            with st.spinner("Gemini analizando nota..."):
                res = procesar_con_gemini(bytes_data, es_imagen=True)
                if res:
                    st.session_state['temp_datos'] = {
                        'nombre': res.get('nombre', res.get('NOMBRE', '')),
                        'tel': re.sub(r'\D', '', str(res.get('tel', res.get('TELÉFONO', '')))),
                        'dir': res.get('dir', res.get('DIRECCIÓN', ''))
                    }
                    st.rerun()

    with col2:
        st.subheader("📝 Confirmar y Guardar")
        
        # EL DICTADO USANDO EL MISMO CEREBRO
        st.write("🎙️ **Corregir o Dictar nota completa:**")
        audio = mic_recorder(start_prompt="Hablar 🎙️", stop_prompt="Parar ⏹️", key='grabadora_gemini')
        
        if audio:
            # Nota: Aquí usamos la transcripción simple para el ejemplo
            # En v4.1 podemos subir el audio directamente a Gemini
            st.info("Procesando dictado...")
            # Simulamos el dictado por ahora o usamos un transcriptor simple
            # Para rapidez, Gemini Texto es mejor aquí
            
        with st.form("registro_gemini"):
            nom = st.text_input("Nombre", value=st.session_state['temp_datos']['nombre'])
            tel = st.text_input("WhatsApp", value=st.session_state['temp_datos']['tel'])
            dire = st.text_input("Dirección", value=st.session_state['temp_datos']['dir'])
            promo = st.selectbox("Estrategia", ["Envío Gratis 🚚", "Bono $5.000 🎁", "Cliente Frecuente ⭐"])
            
            if st.form_submit_button("✅ GUARDAR Y WHATSAPP"):
                st.session_state['db_clientes'].append({
                    "Fecha": datetime.now().strftime("%d/%m %H:%M"),
                    "Cliente": nom, "Tel": tel, "Dir": dire, "Promo": promo
                })
                wa_num = f"57{tel}" if len(tel) == 10 else tel
                msg = f"Hola *{nom}* 🛒, Tropiexpress confirma tu pedido.\n📍 *Dirección:* {dire}\n🎁 *Regalo:* {promo}"
                link = f"https://wa.me/{wa_num}?text={urllib.parse.quote(msg)}"
                st.markdown(f'<a href="{link}" target="_blank"><div style="background-color:#25D366;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">📲 ENVIAR BIENVENIDA</div></a>', unsafe_allow_html=True)

# --- TABLA ---
if st.session_state['db_clientes']:
    st.divider()
    df = pd.DataFrame(st.session_state['db_clientes'])
    st.dataframe(df.iloc[::-1], use_container_width=True)
