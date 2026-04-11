import streamlit as st
import sqlite3
import pandas as pd
import easyocr
import numpy as np
import cv2
from PIL import Image
import re
import urllib.parse
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Tropiexpress v13", page_icon="🛒")
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# Inicializar estados
for key in ['n_v', 't_v', 'd_v']:
    if key not in st.session_state: st.session_state[key] = ""

# --- 2. MOTOR IA MEJORADO (LECTURA LENTA Y PRECISA) ---
@st.cache_resource
def load_ocr_deep():
    # Cargamos el modelo con soporte para mejor detección de párrafos
    return easyocr.Reader(['es'], gpu=False)

def limpiar_profundo(img_pil):
    img_np = np.array(img_pil.convert('RGB'))
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    # Filtro de contraste extremo para resaltar solo la tinta del lapicero
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    res = clahe.apply(gray)
    _, thr = cv2.threshold(res, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thr

# --- 3. INTERFAZ ---
st.title("🛒 Tropiexpress Pro: IA + Voz")

metodo = st.radio("Entrada de imagen:", ["Galería 📁", "Cámara 📸"], horizontal=True)
archivo = st.camera_input("Foto") if metodo == "Cámara 📸" else st.file_uploader("Elegir", type=['jpg', 'png'])

if archivo:
    img_pil = Image.open(archivo)
    img_ready = limpiar_profundo(img_pil)
    st.image(img_ready, caption="Vista de alta definición", width=300)

    if st.button("🔍 ESCANEO PROFUNDO (Priorizar Claridad)"):
        with st.spinner("Analizando trazos..."):
            reader = load_ocr_deep()
            # Ajustamos parámetros para que sea más minucioso
            res = reader.readtext(img_ready, detail=0, paragraph=True, contrast_ths=0.1, adjust_contrast=0.7)
            
            if res:
                texto_full = " ".join(res).lower()
                # Teléfono
                nums = re.sub(r'\D', '', texto_full)
                tel_m = re.search(r'3\d{9}', nums)
                
                # Discriminación de Dirección
                direc_patron = re.compile(r'(calle|cll|cra|carrera|#|nro|no|casa|apto|transversal)', re.I)
                direc_encontrada = ""
                for linea in res:
                    if direc_patron.search(linea):
                        direc_encontrada = linea
                        break

                st.session_state['n_v'] = res[0].capitalize()
                st.session_state['t_v'] = tel_m.group() if tel_m else ""
                st.session_state['d_v'] = direc_encontrada.capitalize()
                st.success("¡Lectura detallada lista!")

st.divider()

# --- 4. FORMULARIO CON APOYO DE VOZ ---
st.subheader("Confirmación de Datos")
st.caption("Tip: Si estás en móvil, usa el micrófono del teclado para dictar en los campos.")

with st.form("form_v13"):
    # Campos de texto
    nombre = st.text_input("Nombre del Cliente", value=st.session_state['n_v'])
    direccion = st.text_input("Dirección de Entrega", value=st.session_state['d_v'])
    whatsapp = st.text_input("WhatsApp", value=st.session_state['t_v'])
    
    promo = st.selectbox("Estrategia de Fidelización", ["Envío Gratis 🚚", "Bono $5.000 🎁", "10% Descuento 💸"])

    if st.form_submit_button("✅ Guardar y Enviar WhatsApp"):
        if nombre and whatsapp:
            # Lógica de guardado (DB)
            conn = sqlite3.connect('tropi_v13.db')
            conn.execute("INSERT OR REPLACE INTO clientes (nombre, direccion, telefono) VALUES (?,?,?)", (nombre, direccion, whatsapp))
            conn.commit()
            
            # Marketing
            msg = f"¡Hola {nombre}! Bienvenido a Tropiexpress. Promo: {promo}. Destino: {direccion}."
            link = f"https://wa.me/57{whatsapp}?text={urllib.parse.quote(msg)}"
            st.markdown(f"### [📲 ENVIAR A WHATSAPP]({link})")
