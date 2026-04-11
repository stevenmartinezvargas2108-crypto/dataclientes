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
st.set_page_config(page_title="Tropiexpress Pro", page_icon="🚀")
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('tropiexpress_mkt_v7.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, nombre TEXT, direccion TEXT, telefono TEXT UNIQUE)''')
    return conn

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False)

db = init_db()
reader = load_ocr()

st.title("🚀 Tropiexpress: IA + Fidelización")

# --- LÓGICA DE EXTRACCIÓN MEJORADA ---
foto = st.camera_input("Capturar datos (Papel)")

if foto:
    img_pil = Image.open(foto)
    img_cv = np.array(img_pil.convert('RGB'))
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
    
    # Pre-procesamiento para que la IA lea mejor
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    processed = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    if st.button("🔍 Escanear con IA"):
        with st.spinner("Leyendo papel..."):
            resultados = reader.readtext(processed)
            texto_full = " ".join([r[1] for r in resultados])
            
            # Extraer Teléfono (10 dígitos)
            nums = re.sub(r'[^0-9]', '', texto_full)
            tel_match = re.search(r'\d{10}', nums)
            
            st.session_state['nom'] = resultados[0][1] if resultados else ""
            st.session_state['tel'] = tel_match.group() if tel_match else ""

st.divider()

# --- FORMULARIO Y MARKETING ---
with st.form("registro"):
    nom = st.text_input("Nombre", value=st.session_state.get('nom', ""))
    tel = st.text_input("WhatsApp (10 dígitos)", value=st.session_state.get('tel', ""))
    dir_e = st.text_input("Dirección de Entrega")
    promo = st.selectbox("Estrategia de Atracción", [
        "10% Descuento Primera Compra",
        "Envío Gratis hoy",
        "Bono de $5.000 para tu próxima compra"
    ])
    
    if st.form_submit_button("✅ Guardar y Enviar Bienvenida"):
        if nom and tel:
            try:
                db.execute("INSERT INTO clientes (nombre, direccion, telefono) VALUES (?,?,?)", (nom, dir_e, tel))
                db.commit()
                st.success("¡Cliente nuevo registrado!")
            except:
                db.execute("UPDATE clientes SET nombre=?, direccion=? WHERE telefono=?", (nom, dir_e, tel))
                db.commit()
                st.warning("Datos actualizados.")

            # Mensaje de Marketing agradable
            msg = (f"¡Hola {nom}! ✨ Bienvenido a Tropiexpress. "
                   f"Por ser tu primer registro, tienes: *{promo}*. "
                   f"Tu pedido va para: {dir_e}. 🛒")
            
            # Codificación segura para evitar el SyntaxError
            msg_encoded = urllib.parse.quote(msg)
            link_wa = f"https://wa.me/57{tel}?text={msg_encoded}"
            
            st.markdown(f"### [📲 Enviar Promo a {nom}]({link_wa})")

# --- TABLA DE DATOS ---
if st.checkbox("Ver Base de Datos"):
    df = pd.read_sql_query("SELECT * FROM clientes", db)
    st.dataframe(df, use_container_width=True)
