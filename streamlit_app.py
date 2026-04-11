import streamlit as st
import sqlite3
import pandas as pd
import easyocr
import numpy as np
from PIL import Image
from datetime import datetime
import re

# --- 1. CONFIGURACIÓN Y PROTECCIÓN ANTI-ERROR ---
st.set_page_config(page_title="Tropiexpress Data", page_icon="🛒", layout="centered")
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# --- 2. BASE DE DATOS (Incluye Dirección) ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('tropiexpress_data_v2.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, direccion TEXT, telefono TEXT)''')
    return conn

conn = init_db()

# --- 3. MOTOR IA LIGERO ---
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False, recog_network='latin_g2')

reader = load_ocr()

# --- 4. INTERFAZ ---
st.title("📱 Registro de Clientes Tropiexpress")

tab1, tab2 = st.tabs(["🆕 Registrar Cliente", "📊 Base de Datos"])

with tab1:
    foto = st.file_uploader("Capturar o subir foto", type=['jpg', 'jpeg', 'png'])
    nombre_sug, tel_sug = "", ""

    if foto:
        img = Image.open(foto)
        st.image(img, width=300)
        if st.button("🔍 Escanear Datos"):
            with st.spinner("Leyendo..."):
                resultado = reader.readtext(np.array(img))
                texto_unido = " ".join([res[1] for res in resultado])
                tel_match = re.search(r'\d{10}', texto_unido.replace(" ", ""))
                if tel_match: tel_sug = tel_match.group()
                if resultado: nombre_sug = resultado[0][1]

    # FORMULARIO CON DIRECCIÓN
    with st.form("registro_cliente", clear_on_submit=True):
        st.subheader("Confirmar Datos")
        nombre_f = st.text_input("Nombre del Cliente", value=nombre_sug)
        direccion_f = st.text_input("Dirección de Entrega") # <--- Recuperado
        telefono_f = st.text_input("WhatsApp (10 dígitos)", value=tel_sug)
        
        if st.form_submit_button("✅ Guardar y Enviar Bienvenida"):
            if nombre_f and telefono_f:
                fecha_reg = datetime.now().strftime("%d/%m/%Y %H:%M")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO clientes (fecha, nombre, direccion, telefono) VALUES (?,?,?,?)", 
                             (fecha_reg, nombre_f, direccion_f, telefono_f))
                conn.commit()
                
                st.success(f"¡{nombre_f} guardado!")
                
                # Enlace de WhatsApp
                msg = f"Hola {nombre_f}, bienvenido a Tropiexpress. Tu pedido será enviado a {direccion_f}. ¡Es un gusto saludarte!"
                tel_wa = telefono_f if telefono_f.startswith('57') else f"57{telefono_f}"
                link_wa = f"https://wa.me/{tel_wa}?text={msg.replace(' ', '%20')}"
                st.markdown(f"### [📲 ENVIAR BIENVENIDA POR WHATSAPP]( {link_wa} )")

with tab2:
    st.subheader("Historial")
    df = pd.read_sql_query("SELECT * FROM clientes ORDER BY id DESC", conn)
    st.dataframe(df, use_container_width=True)
