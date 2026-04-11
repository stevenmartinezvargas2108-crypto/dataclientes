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

# Inyectar meta-tag para bloquear el traductor de Google y evitar el error removeChild
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# --- 2. BASE DE DATOS ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('tropiexpress_data.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, telefono TEXT)''')
    return conn

conn = init_db()

# --- 3. MOTOR DE INTELIGENCIA ARTIFICIAL (VERSIÓN LIGERA) ---
@st.cache_resource
def load_ocr():
    # Usamos 'latin_g2' para que la descarga sea rápida y no sature la RAM de Streamlit
    return easyocr.Reader(['es'], gpu=False, recog_network='latin_g2')

reader = load_ocr()

# --- 4. INTERFAZ PRINCIPAL ---
st.title("📱 Registro de Clientes Tropiexpress")
st.info("Recomendación: Si usas Chrome, desactiva la traducción automática para evitar cierres inesperados.")

tab1, tab2 = st.tabs(["🆕 Registrar Cliente", "📊 Base de Datos"])

with tab1:
    foto = st.file_uploader("Capturar o subir foto de datos", type=['jpg', 'jpeg', 'png'])
    
    # Variables de ayuda para el formulario
    nombre_sugerido = ""
    tel_sugerido = ""

    if foto:
        img = Image.open(foto)
        st.image(img, width=300, caption="Imagen para procesar")
        
        if st.button("🔍 Escanear Datos con IA"):
            with st.spinner("Leyendo información..."):
                # Procesar imagen con EasyOCR
                resultado = reader.readtext(np.array(img))
                texto_unido = " ".join([res[1] for res in resultado])
                
                # Buscar teléfono (10 dígitos)
                tel_match = re.search(r'\d{10}', texto_unido.replace(" ", ""))
                if tel_match:
                    tel_sugerido = tel_match.group()
                
                # Tomar la primera línea como posible nombre
                if resultado:
                    nombre_sugerido = resultado[0][1]
                
                st.write("*Vista previa del texto:*", texto_unido)

    # Formulario de Registro
    with st.form("registro_cliente", clear_on_submit=True):
        st.subheader("Confirmar Datos")
        nombre_final = st.text_input("Nombre del Cliente", value=nombre_sugerido)
        telefono_final = st.text_input("Número de WhatsApp (10 dígitos)", value=tel_sugerido)
        
        if st.form_submit_button("✅ Guardar y Enviar Bienvenida"):
            if nombre_final and len(telefono_final) >= 10:
                try:
                    # Guardar en base de datos
                    fecha_reg = datetime.now().strftime("%d/%m/%Y %H:%M")
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO clientes (fecha, nombre, telefono) VALUES (?,?,?)", 
                                 (fecha_reg, nombre_final, telefono_final))
                    conn.commit()
                    
                    st.success(f"¡{nombre_final} registrado con éxito!")
                    
                    # Generar enlace de WhatsApp con mensaje de bienvenida
                    mensaje = f"Hola {nombre_final}, bienvenido a Tropiexpress. Es un gusto saludarte y tenerte como nuestro cliente."
                    # Formato para enlace: https://wa.me/573001234567?text=Hola...
                    # Nota: Se asume código de país 57 (Colombia) si no se incluye
                    tel_wa = telefono_final if telefono_final.startswith('57') else f"57{telefono_final}"
                    link_wa = f"https://wa.me/{tel_wa}?text={mensaje.replace(' ', '%20')}"
                    
                    st.markdown(f"### [📲 CLICK AQUÍ PARA ENVIAR BIENVENIDA]( {link_wa} )")
                    
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("Asegúrate de poner el nombre y un número válido.")

with tab2:
    st.subheader("Historial de Clientes")
    df = pd.read_sql_query("SELECT fecha as Fecha, nombre as Nombre, telefono as Telefono FROM clientes ORDER BY id DESC", conn)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        # Botón para exportar a Excel/CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Base de Datos", data=csv, file_name="clientes_tropiexpress.csv", mime="text/csv")
    else:
        st.write("No hay clientes registrados todavía.")
