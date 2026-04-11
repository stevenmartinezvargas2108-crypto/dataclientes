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
st.set_page_config(page_title="Tropiexpress Pro", page_icon="🛒")
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('tropiexpress_final.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, nombre TEXT, direccion TEXT, telefono TEXT UNIQUE)''')
    return conn

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False)

db = init_db()
reader = load_ocr()

st.title("🛒 Tropiexpress Pro")
st.write("Registra clientes usando la cámara o subiendo una foto.")

# --- SELECTOR DUAL DE IMAGEN ---
metodo = st.radio("Selecciona método:", ["Subir de Galería 📁", "Usar Cámara 📸"], horizontal=True)

if metodo == "Usar Cámara 📸":
    foto = st.camera_input("Capturar datos")
else:
    foto = st.file_uploader("Elige una imagen", type=['jpg', 'jpeg', 'png'])

# Procesamiento de IA
if foto:
    img_pil = Image.open(foto)
    img_cv = np.array(img_pil.convert('RGB'))
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
    
    # Mejora de contraste para lectura difícil
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    processed = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    if st.button("🔍 Escanear Datos con IA"):
        with st.spinner("Analizando..."):
            resultados = reader.readtext(processed)
            texto_full = " ".join([r[1] for r in resultados])
            
            # Limpiar y buscar teléfono de 10 dígitos
            nums = re.sub(r'[^0-9]', '', texto_full)
            tel_match = re.search(r'\d{10}', nums)
            
            # Guardar en memoria temporal
            st.session_state['n_final'] = resultados[0][1] if resultados else ""
            st.session_state['t_final'] = tel_match.group() if tel_match else ""

st.divider()

# --- FORMULARIO Y FIDELIZACIÓN ---
with st.form("registro_mkt"):
    st.subheader("Confirmar Datos y Promoción")
    
    nombre = st.text_input("Nombre del Cliente", value=st.session_state.get('n_final', ""))
    whatsapp = st.text_input("WhatsApp (10 dígitos)", value=st.session_state.get('t_final', ""))
    direccion = st.text_input("Dirección de Entrega")
    
    # Marketing de atracción
    promo = st.selectbox("Regalo de Bienvenida", [
        "Envío GRATIS hoy mismo 🚚",
        "10% de descuento en esta compra 💸",
        "Bono de $5.000 para mañana 🎁"
    ])
    
    if st.form_submit_button("✅ Guardar y Enviar Promo"):
        if nombre and whatsapp:
            try:
                db.execute("INSERT INTO clientes (nombre, direccion, telefono) VALUES (?,?,?)", 
                           (nombre, direccion, whatsapp))
                db.commit()
                st.success(f"¡{nombre} registrado con éxito!")
            except:
                db.execute("UPDATE clientes SET nombre=?, direccion=? WHERE telefono=?", 
                           (nombre, direccion, whatsapp))
                db.commit()
                st.info("Datos actualizados correctamente.")

            # Mensaje Profesional de WhatsApp
            msg = (f"¡Hola {nombre}! ✨ Bienvenido a *Tropiexpress*. "
                   f"Es un gusto atenderte. Por tu registro, te activamos: *{promo}*. "
                   f"Enviaremos tu pedido a: _{direccion}_. ¡Gracias por preferirnos!")
            
            # Link seguro sin errores de sintaxis
            link = f"https://wa.me/57{whatsapp}?text={urllib.parse.quote(msg)}"
            st.markdown(f"### [📲 Haz clic aquí para enviar bienvenida]({link})")

# --- VISUALIZACIÓN ---
if st.checkbox("Ver listado de clientes"):
    df = pd.read_sql_query("SELECT * FROM clientes", db)
    st.dataframe(df, use_container_width=True)
