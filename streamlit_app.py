import streamlit as st
import sqlite3
import pandas as pd
import easyocr
import numpy as np
from PIL import Image
from datetime import datetime
from io import BytesIO

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="DataClientes Tropiexpress", page_icon="🛒", layout="centered")

# --- BASE DE DATOS ---
conn = sqlite3.connect('tropiexpress_data.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS clientes 
             (id INTEGER PRIMARY KEY, fecha TEXT, punto_venta TEXT, nombre TEXT, direccion TEXT, telefono TEXT UNIQUE)''')
conn.commit()

# --- USUARIOS ---
USUARIOS_AUTORIZADOS = {
    "Sede_Principal": "tropi123",
    "Sede_Sur": "sur456",
    "Admin": "master2026"
}

# --- CARGA DE OCR ---
@st.cache_resource
def get_ocr_reader():
    return easyocr.Reader(['es'], gpu=False)

reader = get_ocr_reader()

# --- LÓGICA DE ACCESO ---
if 'punto_venta' not in st.session_state:
    st.title("🛒 Acceso Tropiexpress")
    with st.form("login"):
        user = st.selectbox("Seleccione Punto de Venta", list(USUARIOS_AUTORIZADOS.keys()))
        password = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar", use_container_width=True):
            if USUARIOS_AUTORIZADOS.get(user) == password:
                st.session_state['punto_venta'] = user
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
else:
    # --- APP PRINCIPAL ---
    st.sidebar.title(f"📍 {st.session_state['punto_venta']}")
    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state['punto_venta']
        st.rerun()

    st.title("📱 Registro de Clientes")
    tab1, tab2 = st.tabs(["🆕 Registro", "📊 Base de Datos"])

    with tab1:
        foto = st.camera_input("Escanear datos")
        if foto:
            img = Image.open(foto)
            with st.spinner("Leyendo..."):
                res = reader.readtext(np.array(img))
                st.info("Texto detectado: " + " ".join([r[1] for r in res]))

        with st.form("form_reg", clear_on_submit=True):
            nombre = st.text_input("Nombre del Cliente")
            direccion = st.text_input("Dirección")
            telefono = st.text_input("WhatsApp (ej: 573001234567)")
            
            if st.form_submit_button("Guardar y Enviar Bienvenida", use_container_width=True):
                if nombre and telefono:
                    try:
                        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                        c.execute("INSERT INTO clientes (fecha, punto_venta, nombre, direccion, telefono) VALUES (?,?,?,?,?)", 
                                  (fecha, st.session_state['punto_venta'], nombre, direccion, telefono))
                        conn.commit()
                        st.success("¡Registrado!")
                        
                        msg = (f"Hola {nombre}, te damos la bienvenida a supermercados tropiexpress. "
                               "Para nosotros es un placer que hagas parte de nuestra familia. "
                               "Agreganos a tu lista de contactos si aun no nos tienes para que conozcas nuestras ofertas.")
                        st.link_button("📲 Enviar WhatsApp", f"https://wa.me/{telefono}?text={msg.replace(' ', '%20')}")
                    except sqlite3.IntegrityError:
                        st.warning("Este cliente ya existe.")

    with tab2:
        query = "SELECT fecha, nombre, direccion, telefono FROM clientes"
        if st.session_state['punto_venta'] != "Admin":
            query += f" WHERE punto_venta = '{st.session_state['punto_venta']}'"
        df = pd.read_sql_query(query, conn)
        st.dataframe(df, use_container_width=True)
        
        if not df.empty:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 Descargar Excel", output.getvalue(), "clientes.xlsx", use_container_width=True)
