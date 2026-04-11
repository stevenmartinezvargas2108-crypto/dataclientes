import streamlit as st
import sqlite3
import pandas as pd
import easyocr
import numpy as np
import cv2
from PIL import Image
import re
import urllib.parse

# --- CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Tropiexpress Control", page_icon="🛒")
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# Inicializar DB y OCR de forma segura
def init_db():
    conn = sqlite3.connect('tropiexpress_data.db', check_same_thread=False)
    conn.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nombre TEXT, direccion TEXT, telefono TEXT UNIQUE)')
    return conn

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False)

db = init_db()
reader = load_ocr()

st.title("🚀 Sistema Tropiexpress")
st.info("Captura o sube la foto del pedido para registrar al cliente.")

# --- SECCIÓN DE ENTRADA ---
opcion = st.selectbox("¿Cómo quieres ingresar la imagen?", ["Subir archivo de Galería", "Tomar Foto con Cámara"])

foto = None
if opcion == "Subir archivo de Galería":
    foto = st.file_uploader("Selecciona la imagen", type=['jpg', 'jpeg', 'png'])
else:
    foto = st.camera_input("Captura el papel")

# --- PROCESAMIENTO CON IA ---
if foto:
    try:
        img = Image.open(foto)
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Filtro para mejorar lectura de manuscritos
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        if st.button("🔍 Extraer Datos"):
            with st.spinner("IA trabajando..."):
                res = reader.readtext(processed)
                texto_total = " ".join([item[1] for item in res])
                
                # Buscar número de 10 dígitos
                telefonos = re.findall(r'\d{10}', texto_total.replace(" ", ""))
                
                st.session_state['n_temp'] = res[0][1] if len(res) > 0 else ""
                st.session_state['t_temp'] = telefonos[0] if telefonos else ""
                st.success("Lectura completada.")
    except Exception as e:
        st.error(f"Error al procesar imagen: {e}")

st.divider()

# --- FORMULARIO FINAL ---
with st.form("form_cliente"):
    c1, c2 = st.columns(2)
    with c1:
        nom = st.text_input("Nombre", value=st.session_state.get('n_temp', ""))
        tel = st.text_input("WhatsApp", value=st.session_state.get('t_temp', ""))
    with c2:
        direc = st.text_input("Dirección")
        promo = st.selectbox("Promo", ["Envío Gratis", "Bono $5.000", "Descuento 10%"])

    if st.form_submit_button("✅ Guardar y Generar Enlace"):
        if nom and tel:
            # Guardar en base de datos
            try:
                db.execute("INSERT OR REPLACE INTO clientes (nombre, direccion, telefono) VALUES (?,?,?)", (nom, direc, tel))
                db.commit()
                
                # Crear mensaje de WhatsApp sin errores de sintaxis
                texto_ws = f"Hola {nom}, bienvenido a Tropiexpress. Tu promo es: {promo}. Entregaremos en: {direc}"
                link = f"https://wa.me/57{tel}?text={urllib.parse.quote(texto_ws)}"
                
                st.success("¡Cliente guardado!")
                st.markdown(f"### [📲 Enviar WhatsApp a {nom}]({link})")
            except Exception as e:
                st.error("No se pudo guardar: " + str(e))

# --- REPORTE ---
if st.expander("Ver base de datos de clientes"):
    df = pd.read_sql_query("SELECT * FROM clientes", db)
    st.dataframe(df, use_container_width=True)
