import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from streamlit_mic_recorder import mic_recorder
import pandas as pd
import re
import urllib.parse
from datetime import datetime
from PIL import Image
import io
import json

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress Master", page_icon="🛒", layout="wide")

# --- 2. INICIALIZACIÓN DE CONEXIONES ---

try:
    # Configuración de la API Key
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    
    # CAMBIO CRÍTICO: Usamos 'gemini-1.5-flash' para evitar el error 404
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Error configurando Gemini API Key: {e}")
    st.stop()

try:
    # Conexión a Google Sheets
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error conectando a Google Sheets: {e}")
    st.stop()

# Inicializar estado de la sesión
if 'temp_datos' not in st.session_state:
    st.session_state['temp_datos'] = {'nombre': '', 'tel': '', 'dir': ''}

# --- 3. FUNCIONES LÓGICAS (IA Y DATOS) ---

def extraer_datos_ia(contenido, tipo="imagen"):
    """Usa Gemini para extraer datos de imagen o audio."""
    prompt = """
    Analiza el contenido adjunto (imagen de nota o audio).
    Extrae el NOMBRE COMPLETO del cliente, su TELÉFONO y su DIRECCIÓN de entrega.
    Responde ÚNICAMENTE con un objeto JSON con este formato:
    {"nombre": "...", "tel": "...", "dir": "..."}
    Si no encuentras un dato, deja el valor vacío "".
    """
    try:
        if tipo == "imagen":
            img = Image.open(io.BytesIO(contenido))
            response = model.generate_content([prompt, img])
        elif tipo == "audio":
            audio_part = {"mime_type": "audio/wav", "data": contenido}
            response = model.generate_content([prompt, audio_part])
        
        # Limpiar la respuesta para obtener solo el JSON
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
    except Exception as e:
        st.error(f"Error en la extracción con IA ({tipo}): {e}")
        return None

# --- 4. INTERFAZ DE USUARIO ---
st.title("🛒 Tropiexpress Master Management")
st.markdown("---")

col_ingreso, col_formulario = st.columns([1, 1])

with col_ingreso:
    st.subheader("📸 Entrada de Datos")
    
    archivo = st.file_uploader("Subir foto de nota de venta", type=['jpg', 'jpeg', 'png'], key="uploader_nota")
    
    if archivo:
        bytes_data = archivo.getvalue()
        st.image(bytes_data, caption="Nota cargada", use_container_width=True)
        if st.button("🚀 ANALIZAR IMAGEN CON IA", use_container_width=True):
            with st.spinner("Gemini leyendo la nota..."):
                datos = extraer_datos_ia(bytes_data, tipo="imagen")
                if datos:
                    st.session_state['temp_datos'] = {
                        'nombre': str(datos.get('nombre', '')).title(),
                        'tel': re.sub(r'\D', '', str(datos.get('tel', ''))),
                        'dir': str(datos.get('dir', ''))
                    }
                    st.toast("Datos extraídos correctamente", icon="📸")
                    st.rerun()

    st.markdown("---")
    st.subheader("🎙️ Respaldo por Voz")
    
    audio_grabado = mic_recorder(
        start_prompt="Empezar a dictar 🎙️",
        stop_prompt="Parar y procesar ⏹️",
        key='grabadora_tropi'
    )

    if audio_grabado:
        with st.spinner("Gemini procesando audio..."):
            datos_audio = extraer_datos_ia(audio_grabado['bytes'], tipo="audio")
            if datos_audio:
                st.session_state['temp_datos'] = {
                    'nombre': datos_audio.get('nombre', st.session_state['temp_datos']['nombre']).title(),
                    'tel': re.sub(r'\D', '', str(datos_audio.get('tel', st.session_state['temp_datos']['tel']))),
                    'dir': datos_audio.get('dir', st.session_state['temp_datos']['dir'])
                }
                st.toast("Datos actualizados por audio", icon="🎙️")
                st.rerun()

with col_formulario:
    st.subheader("📝 Confirmar y Guardar")
    
    with st.form("form_cliente", clear_on_submit=False):
        f_nom = st.text_input("Nombre Completo", value=st.session_state['temp_datos']['nombre'])
        f_tel = st.text_input("Teléfono (10 dígitos)", value=st.session_state['temp_datos']['tel'])
        f_dir = st.text_input("Dirección de Entrega", value=st.session_state['temp_datos']['dir'])
        f_promo = st.selectbox("Estrategia", ["Bienvenida Tropiexpress 🏠", "Envío Gratis 🚚", "Bono $5.000 🎁", "Cliente Frecuente ⭐"])
        
        btn_guardar = st.form_submit_button("✅ GUARDAR EN BASE DE DATOS", use_container_width=True)
        
        if btn_guardar:
            if f_nom and f_tel and len(f_tel) >= 10:
                with st.spinner("Verificando duplicados..."):
                    # Leer datos y limpiar filas vacías ("problema de la última línea")
                    df_nube = conn.read(ttl="0s").dropna(how='all')
                    
                    # Normalizar teléfonos de la base de datos (quitar .0 de floats)
                    df_nube['Telefono'] = df_nube['Telefono'].astype(str).str.replace(r'\.0$', '', regex=True)
                    
                    if f_tel in df_nube['Telefono'].tolist():
                        st.error(f"❌ El teléfono {f_tel} ya existe en la base de datos.")
                    else:
                        fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nuevo_df = pd.DataFrame([{
                            "Fecha": fecha_hoy,
                            "Nombre": f_nom.strip(),
                            "Telefono": f_tel.strip(),
                            "Direccion": f_dir.strip(),
                            "Estrategia": f_promo
                        }])
                        
                        df_actualizado = pd.concat([df_nube, nuevo_df], ignore_index=True)
                        conn.update(data=df_actualizado)
                        
                        st.success(f"🎉 ¡{f_nom} registrado con éxito!")
                        st.session_state['temp_datos'] = {'nombre': '', 'tel': '', 'dir': ''}
                        
                        # Generar Link de WhatsApp
                        msg = f"Bienvenido a Tropiexpress {f_nom} 🛒. Confirmamos tu pedido en: {f_dir}. Tu beneficio: {f_promo}."
                        link_wa = f"https://wa.me/57{f_tel}?text={urllib.parse.quote(msg)}"
                        
                        st.markdown(f'''
                            <a href="{link_wa}" target="_blank" style="text-decoration:none;">
                                <div style="background-color:#25D366;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">
                                    📲 ENVIAR BIENVENIDA WHATSAPP
                                </div>
                            </a>
                        ''', unsafe_allow_html=True)
            else:
                st.warning("Por favor completa Nombre y un Teléfono válido.")

# --- 5. VISUALIZACIÓN ---
st.markdown("---")
st.subheader("📋 Últimos Registros")
try:
    df_ver = conn.read(ttl="5s").dropna(how='all')
    st.dataframe(df_ver.iloc[::-1].head(10), use_container_width=True)
except:
    st.info("Sin registros previos.")
