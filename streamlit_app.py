import streamlit as st
import sqlite3
import pandas as pd
import easyocr
import numpy as np
import cv2
from PIL import Image
import re
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tropiexpress Ultra-Extract", page_icon="🛒")

if 'datos' not in st.session_state:
    st.session_state['datos'] = {'nombre': '', 'tel': '', 'dir': ''}

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False)

def limpiar_inteligente(image_pil):
    # 1. Redimensionar a un tamaño óptimo (ni muy grande para no caerse, ni muy chico para no perder detalle)
    img_np = np.array(image_pil.convert('RGB'))
    img_cv = cv2.resize(img_np, (1200, int(img_np.shape[0] * (1200 / img_np.shape[1]))))
    
    # 2. Convertir a escala de grises
    gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    
    # 3. EL SECRETO: Filtro Adaptativo de Gauss
    # Esto elimina las sombras del papel pero mantiene la nitidez del lapicero
    processed = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 12)
    
    return processed

# --- INTERFAZ ---
st.title("🚀 Tropiexpress: Extracción de Alta Precisión")

archivo = st.file_uploader("Sube la foto del pedido", type=['jpg', 'jpeg', 'png'])

if archivo:
    img_pil = Image.open(archivo)
    img_final = limpiar_inteligente(img_pil)
    st.image(img_final, caption="Imagen Optimizada para Lectura", width=400)

    if st.button("🔍 EXTRAER DATOS AHORA"):
        with st.spinner("Procesando con motor de alta precisión..."):
            reader = load_ocr()
            # Usamos detail=1 para obtener las posiciones y reordenar el texto si es necesario
            res = reader.readtext(img_final, detail=0, paragraph=True)
            
            if res:
                full_text = " ".join(res).lower()
                
                # --- MOTOR DE DISCRIMINACIÓN ---
                # 1. Buscar Celular (10 dígitos que empiezan por 3)
                nums_only = re.sub(r'\D', '', full_text)
                tel_m = re.search(r'3\d{9}', nums_only)
                
                # 2. Buscar Dirección (Buscando patrones de calles/números)
                patron_dir = re.compile(r'(calle|cll|cra|carrera|#|nro|no|apto|casa|piso|trans|diag)', re.I)
                dir_s = ""
                for linea in res:
                    if patron_dir.search(linea) and any(c.isdigit() for c in linea):
                        dir_s = linea.strip()
                        break
                
                # 3. Buscar Nombre (Suele ser la línea que no es dirección ni teléfono)
                nom_s = res[0]
                for linea in res:
                    if len(linea) > 5 and not patron_dir.search(linea) and not re.search(r'3\d{9}', linea):
                        nom_s = linea.strip()
                        break

                st.session_state['datos'] = {
                    'nombre': nom_s.title(),
                    'tel': tel_m.group() if tel_m else "",
                    'dir': dir_s.title()
                }
                st.success("¡Datos extraídos con precisión!")

st.divider()

# --- FORMULARIO DE CONFIRMACIÓN ---
with st.form("registro_tropi"):
    col1, col2 = st.columns(2)
    with col1:
        n = st.text_input("Nombre", value=st.session_state['datos']['nombre'])
        t = st.text_input("WhatsApp", value=st.session_state['datos']['tel'])
    with col2:
        d = st.text_input("Dirección", value=st.session_state['datos']['dir'])
        promo = st.selectbox("Estrategia", ["Envío Gratis 🚚", "Bono $5.000 🎁"])

    if st.form_submit_button("✅ Guardar y Enviar"):
        if n and t:
            # Enlace de WhatsApp seguro
            msg = f"Hola {n}, bienvenido a Tropiexpress. Promo: {promo}. Destino: {d}"
            link = f"https://wa.me/57{t}?text={urllib.parse.quote(msg)}"
            st.markdown(f"### [📲 CLICK PARA WHATSAPP]({link})")
