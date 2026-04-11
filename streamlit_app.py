[9:43 p.m., 10/4/2026] Jhonnathan: import streamlit as st
import sqlite3
import pandas as pd
import easyocr
import numpy as np
from PIL import Image
from datetime import datetime
from io import BytesIO
import re

# --- 1. CAPA DE INMUNIZACIÓN TOTAL (Colocar al puro principio) ---
st.set_page_config(page_title="DataClientes Tropiexpress", page_icon="🛒", layout="centered")

# Inyectar metadatos y CSS para bloquear traductores
st.markdown("""
    <head>
        <meta name="google" content="notranslate">
    </head>
    <style>
        /* Bloquea la traducción en toda la app */
        .stApp {
            unicode-bidi: isolate;
        }
        #root * {
            direction: ltr !important;
            text-align: left !important;
        }
    </style>
    <script>
        // Intento de blo…
[9:49 p.m., 10/4/2026] Jhonnathan: import streamlit as st
import sqlite3
import pandas as pd
import easyocr
import numpy as np
from PIL import Image
from datetime import datetime
from io import BytesIO
import re

# --- 1. CONFIGURACIÓN Y PROTECCIÓN ---
st.set_page_config(page_title="DataClientes Tropiexpress", page_icon="🛒", layout="centered")

# Inyectar protección básica contra traductores
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# --- 2. BASE DE DATOS Y ESTADO ---
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect('tropiexpress_data.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, fecha TEXT, punto_venta TEXT, nombre TEXT, direccion TEXT, telefono TEXT UNIQUE)''')
    return conn

conn = get_db_connection()

for key in ['n_ocr', 'd_ocr', 't_ocr']:
    if key not in st.session_state: st.session_state[key] = ""

# --- 3. CARGA DE OCR ---
@st.cache_resource
def get_ocr_reader():
    return easyocr.Reader(['es'], gpu=False)

reader = get_ocr_reader()

# --- 4. ACCESO ---
USUARIOS = {"Sede_Principal": "tropi123", "Sede_Sur": "sur456", "Admin": "master2026"}

if 'pv' not in st.session_state:
    st.title("🛒 Acceso Tropiexpress")
    with st.form("login"):
        u = st.selectbox("Punto de Venta", list(USUARIOS.keys()))
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            if USUARIOS.get(u) == p:
                st.session_state['pv'] = u
                st.rerun()
            else: st.error("Error de contraseña")
else:
    # --- 5. APLICACIÓN ---
    st.sidebar.title(f"📍 {st.session_state['pv']}")
    if st.sidebar.button("Salir"):
        del st.session_state['pv']
        st.rerun()

    st.title("📱 Registro de Clientes")
    t1, t2 = st.tabs(["🆕 Registro", "📊 Base de Datos"])

    with t1:
        f = st.file_uploader("Foto o Galería", type=['png', 'jpg', 'jpeg'])
        if f:
            img = Image.open(f)
            st.image(img, width=250)
            if st.button("🔍 Extraer Datos"):
                with st.spinner("Procesando..."):
                    res = reader.readtext(np.array(img))
                    txts = [r[1] for r in res]
                    if txts:
                        st.session_state.n_ocr = txts[0]
                        full = " ".join(txts)
                        tel = re.search(r'\d{10}', full.replace(" ", ""))
                        if tel: st.session_state.t_ocr = tel.group()
                        if len(txts) > 1: st.session_state.d_ocr = " ".join(txts[1:3])

        with st.form("f_reg", clear_on_submit=True):
            nom = st.text_input("Nombre", value=st.session_state.n_ocr)
            dir = st.text_input("Dirección", value=st.session_state.d_ocr)
            tel = st.text_input("WhatsApp", value=st.session_state.t_ocr)
            
            if st.form_submit_button("💾 Guardar"):
                if nom and tel:
                    try:
                        cur = conn.cursor()
                        now = datetime.now().strftime("%Y-%m-%d %H:%M")
                        cur.execute("INSERT INTO clientes (fecha, punto_venta, nombre, direccion, telefono) VALUES (?,?,?,?,?)", 
                                  (now, st.session_state['pv'], nom, dir, tel))
                        conn.commit()
                        st.success("¡Registrado!")
                        st.session_state.n_ocr = st.session_state.d_ocr = st.session_state.t_ocr = ""
                        st.link_button("📲 Enviar WhatsApp", f"https://wa.me/{tel}?text=Bienvenido%20a%20Tropiexpress")
                    except: st.warning("El cliente ya existe")

    with t2:
        df = pd.read_sql_query("SELECT * FROM clientes", conn)
        st.dataframe(df)
