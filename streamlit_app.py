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

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress Pro", page_icon="🛒", layout="centered")

# Protección contra el traductor de Google (causa errores removeChild)
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# --- BASE DE DATOS (Fidelización) ---
def init_db():
    conn = sqlite3.connect('tropiexpress_marketing_v3.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, direccion TEXT, telefono TEXT UNIQUE)''')
    return conn

# --- MOTOR IA (Carga lenta para ahorrar RAM) ---
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False)

db = init_db()

# --- INTERFAZ ---
st.title("🚀 Tropiexpress Marketing Pro")
st.write("Registra clientes y fideliza con promociones.")

tab1, tab2 = st.tabs(["📲 Registro Pro", "📊 Base de Datos"])

with tab1:
    # Selector Dual: Cámara o Galería para evitar conflictos
    metodo = st.radio("Método de entrada:", ["Subir Imagen 📁", "Usar Cámara 📸"], horizontal=True)
    
    archivo = None
    if metodo == "Usar Cámara 📸":
        archivo = st.camera_input("Capturar recibo")
    else:
        # Aumentamos el límite de subida a 300MB como pediste, pero el código la procesará
        archivo = st.file_uploader("Selecciona la imagen", type=['jpg', 'jpeg', 'png'], accept_multiple_files=False)

    # --- PROCESAMIENTO DE IA OPTIMIZADO ---
    if archivo:
        try:
            # 1. Cargar y Reducir tamaño para no agotar la RAM
            img_pil = Image.open(archivo)
            img_pil.thumbnail((1200, 1200)) # Ajuste automático a tamaño seguro
            img_np = np.array(img_pil.convert('RGB'))
            img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
            # 2. Pre-procesamiento para lectura difícil
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            # Aumentar contraste y eliminar sombras (Umbral Adaptativo)
            processed_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            st.image(processed_img, caption="Vista optimizada para IA", width=300)

            if st.button("🚀 Escanear Datos con IA"):
                with st.spinner("Despertando a la IA (esto ahorra RAM)..."):
                    reader = load_ocr() # Carga lenta aquí
                    resultados = reader.readtext(processed_img)
                    texto_completo = " ".join([res[1] for res in resultados])
                    
                    # Extraer teléfono (10 dígitos) limpiando caracteres extraños
                    nums = re.sub(r'[^0-9]', '', texto_completo.replace(" ", ""))
                    match_tel = re.search(r'\d{10}', nums)
                    
                    # Guardar en estado de sesión para el formulario
                    st.session_state['n_mkt'] = resultados[0][1] if resultados else ""
                    st.session_state['t_mkt'] = match_tel.group() if match_tel else ""
                    st.success("¡Lectura completada!")

        except Exception as e:
            st.error(f"Error técnico con la imagen (intenta reiniciar la app): {e}")

    st.divider()

    # --- FORMULARIO DE FIDELIZACIÓN ---
    with st.form("registro_mkt", clear_on_submit=False):
        st.subheader("Confirmación y Promo de Bienvenida")
        
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre", value=st.session_state.get('n_mkt', ""))
            whatsapp = st.text_input("WhatsApp (10 dígitos)", value=st.session_state.get('t_mkt', ""))
        with c2:
            direccion = st.text_input("Dirección de Entrega")
            promo = st.selectbox("Estrategia de Fidelización", [
                "Envío Gratis hoy",
                "10% Desc para tu próxima compra",
                "Bono de $5.000 para mañana"
            ])

        if st.form_submit_button("✅ Guardar y Enviar Marketing"):
            if nombre and whatsapp:
                fecha_hoy = datetime.now().strftime("%d/%m/%Y")
                try:
                    # Guardar en base de datos
                    db.execute("INSERT OR REPLACE INTO clientes (fecha, nombre, direccion, telefono) VALUES (?,?,?,?)", 
                               (fecha_hoy, nombre, direccion, whatsapp))
                    db.commit()
                    
                    # Mensaje agradable y vendedor para WhatsApp
                    mensaje = f"Hola {nombre}, bienvenido a Tropiexpress. Es un placer saludarte. Por tu registro, te activamos: {promo}. Tu pedido va para: {direccion}. ¡Gracias por preferirnos! 🛒✨"
                    link_wa = f"https://wa.me/57{whatsapp}?text={urllib.parse.quote(mensaje)}"
                    
                    st.success(f"¡{nombre} registrado con éxito!")
                    st.markdown(f"### [📲 Haz clic aquí para enviar bienvenida]({link_wa})")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

with tab2:
    st.subheader("Comunidad Tropiexpress")
    if st.button("🔄 Actualizar Tabla"):
        df = pd.read_sql_query("SELECT * FROM clientes", db)
        st.dataframe(df, use_container_width=True)
