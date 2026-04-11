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

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tropiexpress IA Pro", page_icon="🚀")

# Estados de sesión para evitar que se borren los datos al procesar
if 'datos' not in st.session_state: 
    st.session_state['datos'] = {'nombre': '', 'tel': '', 'dir': ''}

@st.cache_resource
def load_ocr():
    # Cargamos el modelo una vez para velocidad
    return easyocr.Reader(['es'], gpu=False)

def motor_limpieza(image_pil):
    # 1. Reducir para velocidad (Evita la caída del servidor)
    img_np = np.array(image_pil.convert('RGB'))
    h, w = img_np.shape[:2]
    img_resized = cv2.resize(img_np, (1000, int(h * (1000 / w))))
    
    # 2. Filtro de alta definición para manuscritos
    gray = cv2.cvtColor(img_resized, cv2.COLOR_RGB2GRAY)
    # Eliminamos sombras del papel
    dilated = cv2.dilate(gray, np.ones((7,7), np.uint8))
    bg = cv2.medianBlur(dilated, 21)
    diff = 255 - cv2.absdiff(gray, bg)
    norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    return norm

# --- INTERFAZ ---
st.title("🚀 Tropiexpress: Extracción Inteligente")

archivo = st.file_uploader("Sube la foto del pedido", type=['jpg', 'jpeg', 'png'])

if archivo:
    img_pil = Image.open(archivo)
    img_final = motor_limpieza(img_pil)
    st.image(img_final, caption="Imagen Optimizada", width=350)

    if st.button("🔍 EXTRAER DATOS AHORA"):
        with st.spinner("Analizando como un experto..."):
            reader = load_ocr()
            # Escaneo profundo de párrafos
            resultados = reader.readtext(img_final, detail=0, paragraph=True)
            
            if resultados:
                texto_unido = " ".join(resultados).lower()
                
                # --- MOTOR DE DISCRIMINACIÓN ---
                # 1. Teléfono: 10 dígitos que empiecen por 3
                nums = re.sub(r'\D', '', texto_unido)
                match_tel = re.search(r'3\d{9}', nums)
                
                # 2. Dirección: Palabras clave de Colombia
                patron_dir = re.compile(r'(calle|cll|cra|carrera|#|nro|no|casa|apto|piso|transversal|av)', re.I)
                dir_hallada = ""
                for linea in resultados:
                    if patron_dir.search(linea):
                        dir_hallada = linea.strip()
                        break
                
                # 3. Nombre: Si no hay palabra "Nombre", asumimos que es la primera línea corta
                nombre_hallado = resultados[0]
                for linea in resultados:
                    if "nombre" in linea.lower():
                        nombre_hallado = linea.lower().replace("nombre", "").replace(":", "").strip()
                        break

                st.session_state['datos'] = {
                    'nombre': nombre_hallado.capitalize(),
                    'tel': match_tel.group() if match_tel else "",
                    'dir': dir_hallada.capitalize()
                }
                st.success("¡Datos extraídos con éxito!")

st.divider()

# --- FORMULARIO DE CONFIRMACIÓN ---
with st.form("registro_tropi"):
    col1, col2 = st.columns(2)
    with col1:
        nom = st.text_input("Nombre", value=st.session_state['datos']['nombre'])
        tel = st.text_input("WhatsApp", value=st.session_state['datos']['tel'])
    with col2:
        dire = st.text_input("Dirección", value=st.session_state['datos']['dir'])
        promo = st.selectbox("Estrategia", ["Envío Gratis hoy 🚚", "Bono $5.000 🎁"])

    if st.form_submit_button("✅ Guardar y Enviar WhatsApp"):
        if nom and tel:
            # Guardado en base de datos
            conn = sqlite3.connect('tropiexpress_mkt.db')
            conn.execute("INSERT OR REPLACE INTO clientes (nombre, direccion, telefono) VALUES (?,?,?)", (nom, dire, tel))
            conn.commit()
            
            # WhatsApp Marketing
            msg = f"¡Hola {nom}! Bienvenido a Tropiexpress. Tu beneficio: {promo}. Destino: {dire}."
            link = f"https://wa.me/57{tel}?text={urllib.parse.quote(msg)}"
            st.markdown(f"### [📲 CLICK PARA ENVIAR WHATSAPP]({link})")
