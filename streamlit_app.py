import streamlit as st
import pandas as pd
import easyocr
import numpy as np
from PIL import Image, ImageOps
from datetime import datetime
import re
import urllib.parse
from streamlit_mic_recorder import mic_recorder

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TropiExpress v12.1", page_icon="🛒", layout="wide")

# Carga ligera del OCR
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False) # GPU=False para mayor estabilidad en servidores gratuitos

reader = load_ocr()

# --- MEMORIA ---
if 'base_datos' not in st.session_state:
    st.session_state.base_datos = []
if 'temp_datos' not in st.session_state:
    st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}

# --- FUNCIÓN CRÍTICA: COMPRESIÓN Y OPTIMIZACIÓN ---
def optimizar_y_analizar(imagen_subida):
    try:
        img = Image.open(imagen_subida)
        # 1. Corregir orientación automática
        img = ImageOps.exif_transpose(img)
        # 2. Comprimir imagen (Reducir a un máximo de 1000px de ancho para no saturar la RAM)
        img.thumbnail((1000, 1000))
        # 3. Convertir a escala de grises para que el OCR trabaje menos
        img_gris = img.convert('L')
        
        img_array = np.array(img_gris)
        
        with st.spinner("Analizando nota optimizada..."):
            resultados = reader.readtext(img_array, detail=0)
            texto_sucio = " ".join(resultados)
            
            # Búsqueda de teléfono
            tels = re.findall(r'\d{10}', texto_sucio)
            tel = tels[0] if tels else ""
            
            # Lógica de asignación rápida
            st.session_state.temp_datos['n'] = resultados[0] if len(resultados) > 0 else ""
            st.session_state.temp_datos['t'] = tel
            st.session_state.temp_datos['d'] = resultados[-1] if len(resultados) > 1 else ""
            
            st.toast("✅ Procesado con éxito")
    except Exception as e:
        st.error(f"Error al procesar: {e}. Intenta con una foto más pequeña.")

# --- INTERFAZ ---
st.title("🛒 TropiExpress v12.1")
st.caption("Versión Optimizada: Anti-Errores de Servidor")

col1, col2 = st.columns([1, 1.2], gap="medium")

with col1:
    st.subheader("📸 Entrada de Datos")
    archivo = st.file_uploader("Subir nota (La imagen se comprimirá automáticamente)", type=['jpg', 'jpeg', 'png'])
    
    if archivo:
        if st.button("🚀 PROCESAR IMAGEN", use_container_width=True):
            optimizar_y_analizar(archivo)
            st.rerun()
            
    st.divider()
    st.write("🎙️ **Respaldo por Voz:**")
    mic_recorder(start_prompt="Dictar 🎙️", stop_prompt="Parar ⏹️", key='mic_v12')

with col2:
    st.subheader("📝 Validación de Registro")
    with st.form("form_v12"):
        c_nombre = st.text_input("Nombre", value=st.session_state.temp_datos['n'])
        c_tel = st.text_input("WhatsApp (10 dígitos)", value=st.session_state.temp_datos['t'])
        c_dir = st.text_input("Dirección", value=st.session_state.temp_datos['d'])
        
        if st.form_submit_button("✅ GUARDAR Y ENVIAR", use_container_width=True):
            if c_nombre and c_tel:
                # Evitar duplicados
                existe = any(x['Telefono'] == c_tel for x in st.session_state.base_datos)
                
                if existe:
                    st.warning("Cliente ya registrado anteriormente.")
                    msg = f"Hola *{c_nombre}*, gracias por pedir de nuevo en TropiExpress. Tu pedido va para: {c_dir}"
                else:
                    st.session_state.base_datos.append({
                        "Fecha": datetime.now().strftime("%d/%m/%Y"),
                        "Cliente": c_nombre, "Telefono": c_tel, "Direccion": c_dir
                    })
                    st.success("Nuevo cliente registrado.")
                    msg = f"¡Bienvenido a TropiExpress *{c_nombre}*! Confirmamos tu pedido en: {c_dir}"

                url = f"https://wa.me/57{c_tel}?text={urllib.parse.quote(msg)}"
                st.markdown(f"""<a href="{url}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; padding:12px; border:none; border-radius:8px; font-weight:bold; cursor:pointer;">📲 ENVIAR POR WHATSAPP</button></a>""", unsafe_allow_html=True)
                st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}
            else:
                st.error("Completa Nombre y Teléfono.")

# --- TABLA Y EXPORTACIÓN ---
if st.session_state.base_datos:
    st.divider()
    df = pd.DataFrame(st.session_state.base_datos)
    st.data_editor(df, use_container_width=True, hide_index=True)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 DESCARGAR BASE DE DATOS", data=csv, file_name="pedidos.csv", mime='text/csv', use_container_width=True)
