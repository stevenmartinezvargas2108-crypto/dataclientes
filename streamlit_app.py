import streamlit as st
import sqlite3
import pandas as pd
import easyocr
import numpy as np
from PIL import Image
from datetime import datetime
from io import BytesIO
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="DataClientes Tropiexpress", page_icon="🛒", layout="centered")

# --- BASE DE DATOS ---
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect('tropiexpress_data.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, fecha TEXT, punto_venta TEXT, nombre TEXT, direccion TEXT, telefono TEXT UNIQUE)''')
    return conn

conn = get_db_connection()

# --- USUARIOS ---
USUARIOS_AUTORIZADOS = {
    "Sede_Principal": "tropi123",
    "Sede_Sur": "sur456",
    "Admin": "master2026"
}

# --- CARGA DE OCR ---
@st.cache_resource
def get_ocr_reader():
    # 'es' para español, gpu=False para compatibilidad en servidores sin GPU
    return easyocr.Reader(['es'], gpu=False)

reader = get_ocr_reader()

# --- INICIALIZACIÓN DE VARIABLES DE ESTADO (Para edición de OCR) ---
if 'nombre_ocr' not in st.session_state: st.session_state.nombre_ocr = ""
if 'dir_ocr' not in st.session_state: st.session_state.dir_ocr = ""
if 'tel_ocr' not in st.session_state: st.session_state.tel_ocr = ""

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
        # 1. Cambiado a file_uploader para permitir Galería y Cámara
        archivo = st.file_uploader("Subir foto de datos (Cámara o Galería)", type=['png', 'jpg', 'jpeg'])
        
        if archivo:
            img = Image.open(archivo)
            st.image(img, caption="Imagen cargada", width=250)
            
            if st.button("🔍 Extraer Datos de la Imagen", use_container_width=True):
                with st.spinner("Leyendo manuscrito..."):
                    # paragraph=True ayuda a agrupar líneas de dirección
                    res = reader.readtext(np.array(img), paragraph=False)
                    lineas = [r[1] for r in res]
                    
                    if lineas:
                        # Intento de asignación inteligente
                        st.session_state.nombre_ocr = lineas[0] # Primera línea suele ser nombre
                        
                        full_text = " ".join(lineas)
                        # Buscar teléfono (10 dígitos seguidos)
                        tel_match = re.search(r'\d{10}', full_text.replace(" ", "").replace("-", ""))
                        if tel_match:
                            st.session_state.tel_ocr = tel_match.group()
                        
                        # El resto se intenta poner como dirección
                        if len(lineas) > 1:
                            st.session_state.dir_ocr = " ".join(lineas[1:]) if not tel_match else " ".join([l for l in lineas[1:] if not any(c.isdigit() for c in l)])

        # --- FORMULARIO EDITABLE ---
        st.write("---")
        st.subheader("Confirmar Datos")
        with st.form("form_reg", clear_on_submit=True):
            nombre = st.text_input("Nombre del Cliente", value=st.session_state.nombre_ocr)
            direccion = st.text_input("Dirección", value=st.session_state.dir_ocr)
            telefono = st.text_input("WhatsApp (ej: 573001234567)", value=st.session_state.tel_ocr)
            
            if st.form_submit_button("Guardar y Enviar Bienvenida", use_container_width=True):
                if nombre and telefono:
                    try:
                        c = conn.cursor()
                        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
                        c.execute("INSERT INTO clientes (fecha, punto_venta, nombre, direccion, telefono) VALUES (?,?,?,?,?)", 
                                  (fecha, st.session_state['punto_venta'], nombre, direccion, telefono))
                        conn.commit()
                        
                        st.success(f"✅ ¡{nombre} registrado!")
                        
                        # Limpiar campos de la sesión
                        st.session_state.nombre_ocr = ""
                        st.session_state.dir_ocr = ""
                        st.session_state.tel_ocr = ""
                        
                        # Enlace de WhatsApp
                        msg = (f"Hola {nombre}, te damos la bienvenida a supermercados Tropiexpress. "
                               "Es un placer que hagas parte de nuestra familia. "
                               "Agreganos a tus contactos para conocer nuestras ofertas.")
                        
                        whatsapp_link = f"https://wa.me/{telefono}?text={msg.replace(' ', '%20')}"
                        st.markdown(f"### [📲 Haz clic aquí para enviar WhatsApp a {nombre}]({whatsapp_link})")
                        
                    except sqlite3.IntegrityError:
                        st.warning("⚠️ Este número de teléfono ya está registrado.")
                else:
                    st.error("Faltan datos obligatorios (Nombre y Teléfono).")

    with tab2:
        st.subheader("Registros en Sistema")
        query = "SELECT fecha, nombre, direccion, telefono, punto_venta FROM clientes"
        if st.session_state['punto_venta'] != "Admin":
            query += f" WHERE punto_venta = '{st.session_state['punto_venta']}'"
        
        df = pd.read_sql_query(query, conn)
        st.dataframe(df, use_container_width=True)
        
        if not df.empty:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Clientes')
            
            st.download_button(
                label="📥 Descargar Base de Datos (Excel)",
                data=output.getvalue(),
                file_name=f"clientes_{st.session_state['punto_venta']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
