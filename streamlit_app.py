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

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="Tropiexpress Pro", page_icon="🛒")

# Inicializar estados de sesión para evitar errores de refresco
if 'n_final' not in st.session_state: st.session_state['n_final'] = ""
if 't_final' not in st.session_state: st.session_state['t_final'] = ""

def init_db():
    conn = sqlite3.connect('tropiexpress_v11.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, direccion TEXT, telefono TEXT UNIQUE)''')
    return conn

@st.cache_resource
def load_ocr():
    # Cargamos el modelo una sola vez para ahorrar RAM
    return easyocr.Reader(['es'], gpu=False)

# --- MEJORA DE LECTURA (Versión Ligera) ---
def optimizar_imagen(image_pil):
    # Redimensionar si la imagen es muy grande para evitar caídas por RAM
    img_np = np.array(image_pil.convert('RGB'))
    height, width = img_np.shape[:2]
    if max(height, width) > 1500:
        scale = 1500 / max(height, width)
        img_np = cv2.resize(img_np, (int(width * scale), int(height * scale)))
    
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    # Limpieza de ruido y sombras
    smooth = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(smooth, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return thresh

db = init_db()

# --- INTERFAZ ---
st.title("🛒 Registro Tropiexpress")
metodo = st.radio("Entrada:", ["Cámara 📸", "Galería 📁"], horizontal=True)

archivo = st.camera_input("Foto") if metodo == "Cámara 📸" else st.file_uploader("Subir", type=['jpg', 'png'])

if archivo:
    img_pil = Image.open(archivo)
    img_ready = optimizar_imagen(img_pil)
    st.image(img_ready, caption="Vista para IA", width=300)

    if st.button("🔍 Escanear Datos"):
        with st.spinner("Analizando..."):
            reader = load_ocr()
            # Usamos detail=0 para reducir el uso de memoria en el procesamiento
            res = reader.readtext(img_ready, detail=0, paragraph=True)
            
            if res:
                texto = " ".join(res).lower()
                # Filtrar teléfono de 10 dígitos (Colombia)
                numeros = re.sub(r'\D', '', texto)
                match_tel = re.search(r'3\d{9}', numeros)
                
                # Intentar detectar nombre
                nombre_det = res[0]
                for l in res:
                    if "nombre" in l.lower():
                        nombre_det = l.lower().replace("nombre", "").replace(":", "").strip()
                
                st.session_state['n_final'] = nombre_det.capitalize()
                st.session_state['t_final'] = match_tel.group() if match_tel else ""
                st.success("¡Lectura completa!")

st.divider()

# --- FORMULARIO FINAL ---
with st.form("f_registro"):
    st.subheader("Confirmación y Promo")
    nombre = st.text_input("Nombre", value=st.session_state['n_final'])
    whatsapp = st.text_input("WhatsApp", value=st.session_state['t_final'])
    direccion = st.text_input("Dirección")
    promo = st.selectbox("Estrategia", ["Envío Gratis hoy", "10% Descuento"])

    if st.form_submit_button("✅ Guardar y Enviar Marketing"):
        if nombre and whatsapp:
            try:
                fecha = datetime.now().strftime("%d/%m/%Y")
                db.execute("INSERT OR REPLACE INTO clientes (fecha, nombre, direccion, telefono) VALUES (?,?,?,?)", 
                           (fecha, nombre, direccion, whatsapp))
                db.commit()
                
                msg = f"¡Hola {nombre}! Bienvenido a Tropiexpress. Tu beneficio: {promo}. Pedido a: {direccion}."
                link = f"https://wa.me/57{whatsapp}?text={urllib.parse.quote(msg)}"
                st.markdown(f"[📲 ENVIAR WHATSAPP]({link})")
            except Exception as e:
                st.error(f"Error: {e}")

if st.checkbox("Ver Base de Datos"):
    st.dataframe(pd.read_sql_query("SELECT * FROM clientes", db))
