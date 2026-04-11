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

if 'datos_ia' not in st.session_state:
    st.session_state['datos_ia'] = {'nombre': '', 'tel': '', 'dir': ''}

@st.cache_resource
def load_reader():
    return easyocr.Reader(['es'], gpu=False)

def preprocesamiento_avanzado(image_pil):
    # 1. Convertir y Redimensionar (Vital para velocidad y RAM)
    img_np = np.array(image_pil.convert('RGB'))
    img_cv = cv2.resize(img_np, (1200, int(img_np.shape[0] * (1200 / img_np.shape[1]))))
    
    # 2. Eliminar ruido y sombras (Blanqueo total)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    # Suavizado para unir trazos de lapicero rotos
    smooth = cv2.bilateralFilter(gray, 9, 75, 75)
    # Umbralizado adaptativo (Convierte el papel en blanco puro y el texto en negro sólido)
    thresh = cv2.adaptiveThreshold(smooth, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8)
    
    # 3. Operación morfológica para engrosar un poco la letra manuscrita
    kernel = np.ones((2,2), np.uint8)
    processed = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    return processed

# --- INTERFAZ ---
st.title("🛒 Tropiexpress Master Scanner")

archivo = st.file_uploader("Sube el pedido manuscrito", type=['jpg', 'jpeg', 'png'])

if archivo:
    img_pil = Image.open(archivo)
    img_final = preprocesamiento_avanzado(img_pil)
    st.image(img_final, caption="Imagen Optimizada para IA", width=400)

    if st.button("🚀 EXTRAER CON INTELIGENCIA ARTIFICIAL"):
        with st.spinner("Pensando como un humano..."):
            reader = load_reader()
            # Leemos con 'paragraph=True' para mantener el contexto de la dirección
            resultados = reader.readtext(img_final, detail=0, paragraph=True)
            
            if resultados:
                # Unimos todo para buscar patrones globales
                texto_completo = " ".join(resultados).lower()
                
                # --- MOTOR DE DISCRIMINACIÓN "TIPO GEMINI" ---
                
                # A. Buscar Teléfono (Patrón de 10 dígitos que empiece por 3)
                solo_numeros = re.sub(r'\D', '', texto_completo)
                match_tel = re.search(r'3\d{9}', solo_numeros)
                
                # B. Buscar Dirección (Buscando palabras de calles colombianas)
                patrones_dir = ["calle", "cll", "cra", "carrera", "trans", "trv", "diag", "#", "no", "apto", "piso", "casa", "mz", "sector"]
                dir_sug = ""
                for bloque in resultados:
                    if any(p in bloque.lower() for p in patrones_dir):
                        # Si el bloque tiene un número y una palabra clave, es la dirección
                        if any(char.isdigit() for char in bloque):
                            dir_sug = bloque.strip()
                            break
                
                # C. Buscar Nombre (El primer bloque que no sea dirección y sea texto)
                nom_sug = resultados[0]
                for bloque in resultados:
                    # Si no es dirección y tiene más de 3 letras, probablemente es el nombre
                    if not any(p in bloque.lower() for p in patrones_dir) and len(bloque) > 5:
                        nom_sug = bloque
                        break

                st.session_state['datos_ia'] = {
                    'nombre': nom_sug.title(),
                    'tel': match_tel.group() if match_tel else "",
                    'dir': dir_sug.title()
                }
                st.success("¡Extracción finalizada!")

st.divider()

# --- FORMULARIO DE VERIFICACIÓN ---
with st.form("confirmacion_tropi"):
    st.subheader("Datos del Cliente")
    c1, c2 = st.columns(2)
    with c1:
        nombre_f = st.text_input("Nombre", value=st.session_state['datos_ia']['nombre'])
        tel_f = st.text_input("WhatsApp", value=st.session_state['datos_ia']['tel'])
    with c2:
        dir_f = st.text_input("Dirección", value=st.session_state['datos_ia']['dir'])
        promo = st.selectbox("Estrategia", ["Envío Gratis 🚚", "Descuento 10% 💸"])

    if st.form_submit_button("✅ GUARDAR Y ENVIAR"):
        if nombre_f and tel_f:
            # Guardado en DB y enlace de WhatsApp
            txt_mkt = f"Hola {nombre_f}, bienvenido a Tropiexpress. Promo: {promo}. Destino: {dir_f}"
            link = f"https://wa.me/57{tel_f}?text={urllib.parse.quote(txt_mkt)}"
            st.markdown(f"### [📲 CLICK AQUÍ PARA WHATSAPP]({link})")
