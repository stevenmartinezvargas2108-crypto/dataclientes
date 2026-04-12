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

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Tropiexpress Master", page_icon="🛒", layout="wide")

try:
    # Recuerda tener esta clave en Settings -> Secrets de Streamlit Cloud
    GEMINI_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except Exception:
    st.error("Error: Configura la GOOGLE_API_KEY en los Secrets.")

MODEL_NAME = 'models/gemini-1.5-flash-latest'
model = genai.GenerativeModel(MODEL_NAME)

# Inicialización de la base de datos en la sesión
if 'db_clientes' not in st.session_state:
    st.session_state['db_clientes'] = []
if 'temp_datos' not in st.session_state:
    st.session_state['temp_datos'] = {'nombre': '', 'tel': '', 'dir': ''}

# --- 2. FUNCIONES LÓGICAS ---

def procesar_con_gemini(contenido, tipo="imagen"):
    try:
        if tipo == "imagen":
            img = Image.open(io.BytesIO(contenido))
            prompt = "Extrae NOMBRE, TELÉFONO y DIRECCIÓN. Responde solo JSON: {'nombre': '...', 'tel': '...', 'dir': '...'}"
            response = model.generate_content([prompt, img])
        else:
            audio_parts = {"mime_type": "audio/wav", "data": contenido}
            prompt = "Extrae el nombre, teléfono y dirección del cliente de este audio. Responde solo JSON."
            response = model.generate_content([prompt, audio_parts])
        
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except Exception as e:
        st.error(f"Error con la IA: {e}")
        return None

def exportar_csv():
    df = pd.DataFrame(st.session_state['db_clientes'])
    return df.to_csv(index=False).encode('utf-8')

# --- 3. INTERFAZ DE USUARIO ---
st.title("🛒 Tropiexpress Gemini Management")

archivo = st.file_uploader("📸 Escanear nota de venta", type=['jpg', 'jpeg', 'png'])
col_izq, col_der = st.columns([1, 1])

with col_izq:
    if archivo:
        bytes_data = archivo.getvalue()
        st.image(bytes_data, caption="Nota cargada", use_container_width=True)
        if st.button("🚀 ANALIZAR CON IA", use_container_width=True):
            with st.spinner("Leyendo..."):
                res = procesar_con_gemini(bytes_data, tipo="imagen")
                if res:
                    st.session_state['temp_datos'] = {
                        'nombre': res.get('nombre', ''),
                        'tel': re.sub(r'\D', '', str(res.get('tel', ''))),
                        'dir': res.get('dir', '')
                    }
                    st.rerun()

with col_der:
    st.subheader("📝 Registro de Cliente")
    
    # Dictado
    st.write("🎙️ **¿Corregir por voz?**")
    audio = mic_recorder(start_prompt="Dictar 🎙️", stop_prompt="Procesar ⏹️", key='grabadora_v1')
    if audio:
        with st.spinner("Escuchando..."):
            res_audio = procesar_con_gemini(audio['bytes'], tipo="audio")
            if res_audio:
                st.session_state['temp_datos'] = {
                    'nombre': res_audio.get('nombre', ''),
                    'tel': re.sub(r'\D', '', str(res_audio.get('tel', ''))),
                    'dir': res_audio.get('dir', '')
                }
                st.rerun()

    with st.form("formulario_cliente", clear_on_submit=True):
        f_nom = st.text_input("Nombre Completo", value=st.session_state['temp_datos']['nombre'])
        f_tel = st.text_input("Teléfono / WhatsApp", value=st.session_state['temp_datos']['tel'])
        f_dir = st.text_input("Dirección", value=st.session_state['temp_datos']['dir'])
        f_promo = st.selectbox("Estrategia", ["Envío Gratis 🚚", "Bono $5.000 🎁", "Cliente Frecuente ⭐"])
        
        btn_guardar = st.form_submit_button("✅ GUARDAR Y PREPARAR WHATSAPP")
        
        if btn_guardar:
            # VALIDACIÓN DE DUPLICADOS
            existe = any(c['Tel'] == f_tel for c in st.session_state['db_clientes'])
            
            if existe:
                st.error(f"⚠️ AVISO: El cliente con teléfono {f_tel} ya existe en la lista.")
            elif f_nom and f_tel:
                nuevo_cliente = {
                    "Fecha": datetime.now().strftime("%d/%m %H:%M"),
                    "Cliente": f_nom, "Tel": f_tel, "Dir": f_dir, "Promo": f_promo
                }
                st.session_state['db_clientes'].append(nuevo_cliente)
                st.success("Cliente guardado correctamente.")
                
                # Link de WhatsApp
                wa_num = f"57{f_tel}" if len(f_tel) == 10 else f_tel
                msg = f"Hola *{f_nom}* 🛒, Tropiexpress confirma tu pedido.\n📍 *Dirección:* {f_dir}\n🎁 *Regalo:* {f_promo}"
                link = f"https://wa.me/{wa_num}?text={urllib.parse.quote(msg)}"
                st.markdown(f'<a href="{link}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;">📲 ENVIAR BIENVENIDA</div></a>', unsafe_allow_html=True)
            else:
                st.warning("Nombre y Teléfono son obligatorios.")

# --- 4. GESTIÓN DE BASE DE DATOS ---
st.divider()
if st.session_state['db_clientes']:
    st.subheader("📋 Base de Datos de Clientes")
    df = pd.DataFrame(st.session_state['db_clientes'])
    
    # Comandos de Exportación
    col_exp1, col_exp2 = st.columns([1, 4])
    with col_exp1:
        st.download_button(label="📥 Exportar Excel (CSV)", data=exportar_csv(), file_name="clientes_tropiexpress.csv", mime="text/csv")
    
    # Mostrar tabla (invertida para ver los últimos primero)
    st.dataframe(df.iloc[::-1], use_container_width=True)

    # Comando para editar/eliminar (Simplificado)
    with st.expander("🛠️ Opciones de Edición"):
        idx_eliminar = st.number_input("Ingresa el índice de la fila para borrar (0 es el primero)", min_value=0, max_value=len(df)-1, step=1)
        if st.button("🗑️ Eliminar Registro Seleccionado"):
            st.session_state['db_clientes'].pop(int(idx_eliminar))
            st.rerun()
else:
    st.info("Aún no hay clientes registrados hoy.")
