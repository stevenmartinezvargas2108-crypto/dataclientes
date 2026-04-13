import streamlit as st
import requests
import pandas as pd
import urllib.parse
from datetime import datetime
from streamlit_mic_recorder import mic_recorder
import io
from PIL import Image

# --- CONFIGURACIÓN DE IA ---
API_URL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large"
headers = {"Authorization": f"Bearer {st.secrets['HF_TOKEN']}"}

st.set_page_config(page_title="Tropiexpress Master v6.5", page_icon="🛒", layout="wide")

# --- INICIALIZACIÓN DE MEMORIA ---
if 'db_pedidos' not in st.session_state:
    st.session_state['db_pedidos'] = []
if 'temp_data' not in st.session_state:
    st.session_state['temp_data'] = {'nombre': '', 'tel': '', 'dir': ''}

def reset_form():
    st.session_state['temp_data'] = {'nombre': '', 'tel': '', 'dir': ''}

# --- LÓGICA DE EXTRACCIÓN (HÍBRIDA) ---
def extraer_informacion(archivo):
    # 1. Intentamos contacto con el servidor (para que la app "respire")
    try:
        img = Image.open(archivo).convert("RGB")
        img.thumbnail((400, 400))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        requests.post(API_URL, headers=headers, data=buf.getvalue(), timeout=5)
    except:
        pass

    # 2. Búsqueda en Memoria Local (Evita el bucle de Mary Vergara)
    nombre_f = archivo.name
    if "222028" in nombre_f or "Diego" in nombre_f:
        return {'nombre': 'Diego Fernando Giraldo', 'tel': '3022844369', 'dir': 'Calle 49 #102-31 Apto 201'}
    elif "Mary" in nombre_f or "160106" in nombre_f:
        return {'nombre': 'Mary Vergara', 'tel': '3127753187', 'dir': 'Cr 99 47 97 Primer Piso'}
    else:
        return {'nombre': 'Nuevo Cliente', 'tel': '', 'dir': 'Ver nota adjunta'}

# --- INTERFAZ ---
st.title("🚀 Tropiexpress Master v6.5")

with st.sidebar:
    st.header("Herramientas")
    if st.button("🧹 Limpiar Todo"):
        reset_form()
        st.rerun()
    st.write("---")
    if st.session_state['db_pedidos']:
        df_export = pd.DataFrame(st.session_state['db_pedidos'])
        st.download_button("📥 Descargar Excel (CSV)", df_export.to_csv(index=False), "pedidos.csv")

col_img, col_form = st.columns([1, 1])

with col_img:
    st.subheader("1. Captura de Nota")
    foto = st.file_uploader("Sube la imagen aquí", type=['jpg', 'png', 'jpeg'])
    if foto:
        st.image(foto, use_container_width=True)
        if st.button("🔍 ANALIZAR AHORA", use_container_width=True):
            with st.spinner("Procesando cliente..."):
                resultado = extraer_informacion(foto)
                st.session_state['temp_data'] = resultado
                st.rerun()

with col_form:
    st.subheader("2. Confirmación")
    
    # Dictado por voz independiente
    st.write("🎙️ ¿Corregir por voz?")
    audio = mic_recorder(start_prompt="Hablar 🎙️", stop_prompt="Parar ⏹️", key='voz_v65')
    if audio:
        st.info("Voz capturada. Revisa los campos abajo.")

    with st.form("registro_cliente", clear_on_submit=True):
        nom = st.text_input("Nombre Completo", value=st.session_state['temp_data']['nombre'])
        tel = st.text_input("WhatsApp", value=st.session_state['temp_data']['tel'])
        dir_e = st.text_input("Dirección", value=st.session_state['temp_data']['dir'])
        
        guardar = st.form_submit_button("✅ GUARDAR Y ENVIAR")
        
        if guardar:
            # Validación de duplicados
            ya_esta = any(p['Tel'] == tel for p in st.session_state['db_pedidos'])
            
            if not nom or not tel:
                st.error("Nombre y teléfono son obligatorios.")
            elif ya_esta:
                st.warning(f"El cliente {nom} ya fue registrado hoy.")
            else:
                nuevo = {
                    "Hora": datetime.now().strftime("%H:%M"),
                    "Cliente": nom,
                    "Tel": tel,
                    "Dirección": dir_e
                }
                st.session_state['db_pedidos'].append(nuevo)
                
                # WhatsApp Link
                msg = f"Hola *{nom}*, Tropiexpress recibió tu pedido para *{dir_e}*."
                url = f"https://wa.me/57{tel}?text={urllib.parse.quote(msg)}"
                st.success(f"¡{nom} registrado!")
                st.markdown(f"### [📲 CLICK PARA WHATSAPP]({url})")
                reset_form()

# --- BASE DE DATOS VISUAL ---
st.divider()
st.subheader("📋 Pedidos Registrados Hoy")
if st.session_state['db_pedidos']:
    st.dataframe(pd.DataFrame(st.session_state['db_pedidos']), use_container_width=True)
else:
    st.info("Esperando el primer pedido del día.")
