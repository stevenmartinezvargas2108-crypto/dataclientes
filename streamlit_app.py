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

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress Pro", page_icon="🛒", layout="centered")
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# --- 2. BASE DE DATOS (Fidelización) ---
def init_db():
    conn = sqlite3.connect('tropiexpress_final_v11.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, direccion TEXT, telefono TEXT UNIQUE)''')
    return conn

# --- 3. MOTOR IA (Carga optimizada) ---
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False)

# --- 4. FUNCIÓN DE LIMPIEZA DE IMAGEN (La clave de la lectura) ---
def optimizar_para_ocr(image_pil):
    # Convertir a formato OpenCV
    img_np = np.array(image_pil.convert('RGB'))
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    
    # Técnica de blanqueo: elimina sombras y resalta tinta
    dilated = cv2.dilate(gray, np.ones((7,7), np.uint8))
    bg_img = cv2.medianBlur(dilated, 21)
    diff_img = 255 - cv2.absdiff(gray, bg_img)
    norm_img = cv2.normalize(diff_img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    
    # Umbralizado para texto puro
    _, final_thr = cv2.threshold(norm_img, 220, 255, cv2.THRESH_BINARY)
    return final_thr

db = init_db()

# --- 5. INTERFAZ DE USUARIO ---
st.title("🚀 Tropiexpress: Registro & Marketing")
st.info("Sube o toma la foto del pedido para extraer los datos.")

# Selector de entrada para evitar conflictos de hardware
metodo = st.radio("Método de entrada:", ["Subir de Galería 📁", "Usar Cámara 📸"], horizontal=True)

archivo = st.camera_input("Capturar") if metodo == "Usar Cámara 📸" else st.file_uploader("Elegir imagen", type=['jpg', 'jpeg', 'png'])

if archivo:
    try:
        img_pil = Image.open(archivo)
        # Procesar imagen con el nuevo motor de limpieza
        img_limpia = optimizar_para_ocr(img_pil)
        
        st.image(img_limpia, caption="Vista optimizada para el escáner", width=350)

        if st.button("🔍 Escanear Datos con IA"):
            with st.spinner("Leyendo manuscrito..."):
                reader = load_ocr()
                # detail=0 y paragraph=True mejoran la comprensión de nombres
                resultados = reader.readtext(img_limpia, detail=0, paragraph=True)
                
                if resultados:
                    texto_completo = " ".join(resultados).lower()
                    
                    # Extraer teléfono (10 dígitos que empiecen por 3 en Colombia)
                    solo_nums = re.sub(r'\D', '', texto_completo)
                    match_tel = re.search(r'3\d{9}', solo_nums)
                    
                    # Extraer nombre (primera línea o después de 'Nombre:')
                    nombre_sug = resultados[0]
                    for linea in resultados:
                        if "nombre" in linea.lower():
                            nombre_sug = linea.lower().replace("nombre", "").replace(":", "").replace("=", "").strip()
                            break
                    
                    st.session_state['n_final'] = nombre_sug.capitalize()
                    st.session_state['t_final'] = match_tel.group() if match_tel else ""
                    st.success("¡Datos extraídos con éxito!")

    except Exception as e:
        st.error(f"Error al procesar la imagen: {e}")

st.divider()

# --- 6. FORMULARIO Y ESTRATEGIA DE MARKETING ---
with st.form("registro_mkt"):
    st.subheader("Confirmar y Fidelizar")
    c1, c2 = st.columns(2)
    
    with c1:
        nombre = st.text_input("Nombre del Cliente", value=st.session_state.get('n_final', ""))
        whatsapp = st.text_input("WhatsApp (10 dígitos)", value=st.session_state.get('t_final', ""))
    with c2:
        direccion = st.text_input("Dirección de Entrega")
        promo = st.selectbox("Regalo de Bienvenida", [
            "Envío GRATIS hoy mismo 🚚",
            "10% de descuento en esta compra 💸",
            "Bono de $5.000 para mañana 🎁"
        ])

    if st.form_submit_button("✅ Guardar y Enviar Bienvenida"):
        if nombre and whatsapp:
            try:
                fecha_hoy = datetime.now().strftime("%d/%m/%Y")
                db.execute("INSERT OR REPLACE INTO clientes (fecha, nombre, direccion, telefono) VALUES (?,?,?,?)", 
                           (fecha_hoy, nombre, direccion, whatsapp))
                db.commit()
                
                # Mensaje de marketing optimizado
                mensaje = (f"¡Hola {nombre}! ✨ Bienvenido a Tropiexpress. "
                           f"Es un gusto atenderte. Por tu registro, te activamos: {promo}. "
                           f"Enviaremos tu pedido a: {direccion}. ¡Gracias por preferirnos!")
                
                link_wa = f"https://wa.me/57{whatsapp}?text={urllib.parse.quote(mensaje)}"
                
                st.success(f"¡{nombre} guardado!")
                st.markdown(f"### [📲 CLICK AQUÍ PARA WHATSAPP]({link_wa})")
            except Exception as e:
                st.error(f"No se pudo guardar: {e}")

# --- 7. VISUALIZACIÓN DE BASE DE DATOS ---
if st.checkbox("Ver listado de clientes"):
    df = pd.read_sql_query("SELECT * FROM clientes ORDER BY id DESC", db)
    st.dataframe(df, use_container_width=True)
