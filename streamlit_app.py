import streamlit as st
import pandas as pd
import easyocr
import cv2
import numpy as np
from PIL import Image, ImageOps
from datetime import datetime
import re
import urllib.parse
from streamlit_mic_recorder import mic_recorder

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="TropiExpress v12.5", page_icon="🛒", layout="wide")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False)

reader = load_ocr()

if 'base_datos' not in st.session_state:
    st.session_state.base_datos = []
if 'temp_datos' not in st.session_state:
    st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}

# --- MEJORA 1: LIMPIEZA DE IMAGEN (THRESHOLD) ---
def pre_procesar_imagen(pil_image):
    # Convertir a array de OpenCV
    img = np.array(pil_image.convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # Aplicar filtro para resaltar texto manuscrito y eliminar sombras
    # Esto ayuda a que el OCR no confunda letras con manchas
    processed_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return processed_img

def analizar_nota_mejorada(archivo):
    img_orig = Image.open(archivo)
    img_orig = ImageOps.exif_transpose(img_orig)
    img_orig.thumbnail((1200, 1200))
    
    # Pre-procesar
    img_limpia = pre_procesar_imagen(img_orig)
    
    with st.spinner("Limpiando y leyendo nota..."):
        resultados = reader.readtext(img_limpia, detail=0, paragraph=True)
        texto_completo = " ".join(resultados).lower()
        
        # Búsqueda inteligente de teléfono
        tels = re.findall(r'\d{7,10}', texto_completo)
        tel = tels[0] if tels else ""
        
        # Intentar extraer nombre (usualmente cerca de la palabra "nombre" o al inicio)
        # Si el OCR leyó "nombre: juan", extraemos solo "juan"
        nombre_match = re.search(r'nombre[:\s]+([a-z\s]+)', texto_completo)
        nombre = nombre_match.group(1).strip().title() if nombre_match else resultados[0].title()
        
        # Dirección
        dir_match = re.search(r'direcci[oó]n[:\s]+(.+)', texto_completo)
        direccion = dir_match.group(1).strip().upper() if dir_match else resultados[-1].upper()

        st.session_state.temp_datos = {'n': nombre, 't': tel, 'd': direccion}

# --- MEJORA 2: AUTOCOMPLETADO POR VOZ ---
def procesar_voz(texto_transcrito):
    texto = texto_transcrito.lower()
    # Si dictas: "Nombre Pedro Telefono 312 Direccion Calle 10"
    n = re.search(r'nombre\s+([\w\s]+?)(?=\s+tel|$)', texto)
    t = re.search(r'(?:teléfono|telefono|celular)\s+(\d+)', texto)
    d = re.search(r'(?:dirección|direccion|calle)\s+(.+)', texto)
    
    if n: st.session_state.temp_datos['n'] = n.group(1).strip().title()
    if t: st.session_state.temp_datos['t'] = t.group(1).strip()
    if d: st.session_state.temp_datos['d'] = d.group(1).strip().upper()

# --- INTERFAZ ---
st.title("🛒 TropiExpress v12.5 (OCR Pro)")

c1, c2 = st.columns([1, 1.2])

with c1:
    st.subheader("📸 Escáner de Notas")
    foto = st.file_uploader("Subir nota", type=['jpg', 'png', 'jpeg'])
    if foto:
        if st.button("🚀 TRATAR Y LEER IMAGEN", use_container_width=True):
            analizar_nota_mejorada(foto)
            st.rerun()
            
    st.divider()
    st.subheader("🎙️ Dictado Inteligente")
    st.write("Dí: 'Nombre... Teléfono... Dirección...'")
    # Nota: El mic_recorder de streamlit no transcribe solo, 
    # pero aquí preparamos el campo para cuando uses el dictado del teclado del celular.
    voz_input = st.text_area("Si dictas con el teclado, pega aquí para autocompletar:", 
                             placeholder="Ej: Nombre Carlos Telefono 310 Direccion Cra 50")
    if st.button("🪄 AUTOCOMPLETAR DESDE TEXTO"):
        procesar_voz(voz_input)
        st.rerun()

with c2:
    st.subheader("📝 Verificación")
    with st.form("registro_v125"):
        c_nom = st.text_input("Nombre", value=st.session_state.temp_datos['n'])
        c_tel = st.text_input("WhatsApp", value=st.session_state.temp_datos['t'])
        c_dir = st.text_input("Dirección", value=st.session_state.temp_datos['d'])
        
        if st.form_submit_button("✅ GUARDAR PEDIDO", use_container_width=True):
            if c_nom and c_tel:
                # Lógica de duplicados y WhatsApp...
                st.session_state.base_datos.append({
                    "Fecha": datetime.now().strftime("%d/%m"),
                    "Cliente": c_nom, "Tel": c_tel, "Dir": c_dir
                })
                st.success("Guardado en Base de Datos")
                st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}
                st.rerun()

# --- TABLA ---
if st.session_state.base_datos:
    st.divider()
    st.dataframe(pd.DataFrame(st.session_state.base_datos), use_container_width=True)
