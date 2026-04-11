import streamlit as st
import sqlite3
import pandas as pd
import easyocr
import numpy as np
from PIL import Image
from datetime import datetime
import re

# --- 1. CONFIGURACIÓN DE PÁGINA E INMUNIZACIÓN ---
st.set_page_config(page_title="Tropiexpress Data", page_icon="🛒", layout="centered")

# Esta línea es vital para que Google Chrome no intente traducir y rompa la app
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# --- 2. BASE DE DATOS (Optimizada) ---
@st.cache_resource
def get_db():
    conn = sqlite3.connect('tropiexpress_pro.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, direccion TEXT, telefono TEXT)''')
    return conn

conn = get_db()

# --- 3. MOTOR DE LECTURA (Versión Ligera) ---
@st.cache_resource
def load_light_ocr():
    # Usamos 'latin_g2' que es el modelo más liviano disponible para evitar "Oh no" por falta de RAM
    return easyocr.Reader(['es'], gpu=False, recog_network='latin_g2')

reader = load_light_ocr()

# --- 4. INTERFAZ DE USUARIO ---
st.title("🛒 Registro de Clientes Tropiexpress")
st.info("Sugerencia: Si usas el celular, usa el modo Incógnito para evitar errores de traducción.")

tab1, tab2 = st.tabs(["🆕 Nuevo Registro", "📊 Base de Datos"])

with tab1:
    archivo = st.file_uploader("Cargar foto del cliente", type=['jpg', 'jpeg', 'png'])
    
    # Variables temporales para el formulario
    v_nombre, v_dir, v_tel = "", "", ""

    if archivo:
        img = Image.open(archivo)
        st.image(img, caption="Imagen cargada", width=300)
        
        if st.button("🔍 Escanear Datos"):
            with st.spinner("Analizando con IA ligera..."):
                # Procesamiento de imagen
                img_array = np.array(img)
                resultado = reader.readtext(img_array)
                
                # Unimos todo el texto detectado
                texto_completo = " ".join([res[1] for res in resultado])
                st.write("*Texto detectado:*", texto_completo)
                
                # Intentar extraer teléfono (busca 10 números seguidos)
                tel_match = re.search(r'\d{10}', texto_completo.replace(" ", ""))
                if tel_match:
                    v_tel = tel_match.group()
                
                # Intentar sacar el nombre (usualmente la primera línea)
                if len(resultado) > 0:
                    v_nombre = resultado[0][1]

    # Formulario de guardado
    with st.form("form_cliente", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre Completo", value=v_nombre)
            direccion = st.text_input("Dirección")
        with col2:
            telefono = st.text_input("WhatsApp / Teléfono", value=v_tel)
            
        if st.form_submit_button("💾 Guardar en Sistema"):
            if nombre and telefono:
                try:
                    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO clientes (fecha, nombre, direccion, telefono) VALUES (?,?,?,?)",
                                 (fecha_hoy, nombre, direccion, telefono))
                    conn.commit()
                    st.success(f"✅ Cliente {nombre} guardado correctamente.")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("Por favor rellena Nombre y Teléfono.")

with tab2:
    st.subheader("Clientes Registrados")
    try:
        df = pd.read_sql_query("SELECT * FROM clientes ORDER BY id DESC", conn)
        st.dataframe(df, use_container_width=True)
        
        # Opción para descargar en Excel
        if not df.empty:
            st.download_button(
                label="📥 Descargar Base de Datos (Excel)",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name=f"clientes_tropiexpress_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    except:
        st.write("Aún no hay datos registrados.")
