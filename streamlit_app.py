import streamlit as st
import sqlite3
import pandas as pd
import easyocr
import numpy as np
from PIL import Image
from datetime import datetime
import re

# Configuración y bloqueo de traductor para evitar error removeChild
st.set_page_config(page_title="Tropiexpress Data", page_icon="🛒")
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# Base de datos v4 (Limpia)
def init_db():
    conn = sqlite3.connect('tropiexpress_v4.db', check_same_thread=False)
    conn.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, direccion TEXT, telefono TEXT)')
    return conn

# Carga lenta de IA para no bloquear el servidor
@st.cache_resource
def load_reader():
    return easyocr.Reader(['es'], gpu=False, recog_network='latin_g2')

conn = init_db()
reader = load_reader()

st.title("🛒 Registro Tropiexpress")

tab1, tab2 = st.tabs(["📝 Nuevo Cliente", "📋 Listado"])

with tab1:
    foto = st.file_uploader("Subir foto de datos", type=['jpg', 'png', 'jpeg'])
    n_sug, t_sug = "", ""

    if foto:
        img = Image.open(foto)
        st.image(img, width=250)
        if st.button("🔍 Escanear Datos"):
            with st.spinner("Procesando..."):
                res = reader.readtext(np.array(img))
                txt = " ".join([r[1] for r in res])
                tel_m = re.search(r'\d{10}', txt.replace(" ", ""))
                if tel_m: t_sug = tel_m.group()
                if res: n_sug = res[0][1]

    with st.form("form_registro", clear_on_submit=True):
        nombre = st.text_input("Nombre completo", value=n_sug)
        direccion = st.text_input("Dirección de entrega")
        whatsapp = st.text_input("WhatsApp (10 dígitos)", value=t_sug)
        
        if st.form_submit_button("✅ Guardar y Enviar Bienvenida"):
            if nombre and whatsapp:
                fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
                conn.execute("INSERT INTO clientes (fecha, nombre, direccion, telefono) VALUES (?,?,?,?)", 
                             (fecha, nombre, direccion, whatsapp))
                conn.commit()
                st.success(f"¡{nombre} registrado!")
                
                # Link de WhatsApp con mensaje personalizado
                msg = f"Hola {nombre}, bienvenido a Tropiexpress. Guardamos tu dirección: {direccion}. ¡Gracias por preferirnos!"
                link = f"https://wa.me/57{whatsapp}?text={msg.replace(' ', '%20')}"
                st.markdown(f"### [📲 CLICK AQUÍ PARA WHATSAPP]({link})")

with tab2:
    if st.button("Actualizar Lista"):
        df = pd.read_sql_query("SELECT * FROM clientes ORDER BY id DESC", conn)
        st.dataframe(df)
