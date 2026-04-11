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
st.set_page_config(page_title="Tropiexpress v12", page_icon="🛒", layout="centered")
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# Inicializar estados de sesión para el formulario
if 'n_ia' not in st.session_state: st.session_state['n_ia'] = ""
if 't_ia' not in st.session_state: st.session_state['t_ia'] = ""
if 'd_ia' not in st.session_state: st.session_state['d_ia'] = ""

# --- BASE DE DATOS (Fidelización) ---
def init_db():
    # Usamos una base de datos nueva para esta versión mejorada
    conn = sqlite3.connect('tropiexpress_mkt_v12.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, direccion TEXT, telefono TEXT UNIQUE)''')
    return conn

# --- MOTOR IA (Carga optimizada) ---
@st.cache_resource
def load_ocr():
    # detail=0 devuelve solo el texto, lo que ahorra RAM y errores
    return easyocr.Reader(['es'], gpu=False)

# --- FUNCIÓN DE LIMPIEZA PROFUNDA (Clave para manuscritos) ---
def optimizar_lectura(image_pil):
    # Convertir a formato OpenCV
    img_np = np.array(image_pil.convert('RGB'))
    img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    
    # Redimensionar para no agotar RAM si la foto es pesada
    height, width = img_cv.shape[:2]
    if max(height, width) > 1200:
        scale = 1200 / max(height, width)
        img_cv = cv2.resize(img_cv, (int(width * scale), int(height * scale)))

    # Escala de grises
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # Limpieza de fondo: Blanquea el papel y resalta la tinta negra
    dilated = cv2.dilate(gray, np.ones((7,7), np.uint8))
    bg_img = cv2.medianBlur(dilated, 21)
    diff_img = 255 - cv2.absdiff(gray, bg_img)
    norm_img = cv2.normalize(diff_img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
    
    # Umbralizado binario (Solo tinta negra sobre blanco puro)
    _, thr_img = cv2.threshold(norm_img, 225, 255, cv2.THRESH_BINARY)
    return thr_img

db = init_db()
reader = load_ocr()

# --- INTERFAZ Tropiexpress ---
st.title("🛒 Registro Tropiexpress Marketing")
st.write("Sube o toma la foto para extraer y fidelizar al cliente.")

tab1, tab2 = st.tabs(["📝 Registro Pro", "📋 Base de Datos"])

with tab1:
    # Selector Dual para evitar conflictos
    metodo = st.radio("Entrada:", ["Subir Imagen 📁", "Cámara Directa 📸"], horizontal=True)
    archivo = None
    if metodo == "Cámara Directa 📸":
        archivo = st.camera_input("Capturar recibo")
    else:
        archivo = st.file_uploader("Sube la imagen", type=['jpg', 'jpeg', 'png'])

    # --- PROCESAMIENTO DE IA OPTIMIZADO ---
    if archivo:
        try:
            img_pil = Image.open(archivo)
            # Aplicar la limpieza profunda de fondo
            img_ia = optimizar_lectura(img_pil)
            
            # Mostramos la vista optimizada (limpia)
            st.image(img_ia, caption="Vista de alta precisión para IA", width=350)

            if st.button("🔍 Escanear Datos y Discriminado"):
                with st.spinner("Analizando manuscrito..."):
                    # paragraph=True ayuda a extraer líneas completas como 'Nombre' y 'Dirección'
                    resultados = reader.readtext(img_ia, detail=0, paragraph=True)
                    texto_completo = " ".join(resultados).lower()
                    st.session_state['texto_completo'] = texto_completo # Para ver qué detectó

                    # LÓGICA DE EXTRACCIÓN MEJORADA
                    n_sug, t_sug, d_sug = "", "", ""
                    
                    # 1. Teléfono (Colombia: 10 dígitos que empiecen por 3)
                    numeros = re.sub(r'\D', '', texto_completo.replace(" ", ""))
                    match_tel = re.search(r'3\d{9}', numeros)
                    if match_tel: t_sug = match_tel.group()
                    
                    # 2. Dirección (Buscar Calle, Carrera, Nro, # o Apto)
                    patron_dir = re.compile(r'(calle|cll|carrera|cra|av|avenida|#|no|nro|apto|interior|torre)\s?(\d+|[a-z]+)', re.IGNORECASE)
                    
                    for l in resultados:
                        if patron_dir.search(l):
                            d_sug = l.strip()
                            # Limpiar palabras clave de la IA si las detectó
                            d_sug = d_sug.lower().replace("dirección", "").replace("direccion", "").replace(":", "").replace("=", "").strip()
                            break
                    
                    # 3. Nombre (Suele ser lo primero, o después de la palabra 'Nombre')
                    if resultados:
                        nombre_raw = resultados[0]
                        for l in resultados:
                            if "nombre" in l.lower():
                                nombre_raw = l.lower().replace("nombre", "").replace(":", "").replace("=", "").strip()
                                break
                        n_sug = nombre_raw

                    # Guardar en estado de sesión para el formulario
                    st.session_state['n_ia'] = n_sug.capitalize()
                    st.session_state['t_ia'] = t_sug
                    st.session_state['d_ia'] = d_sug.capitalize()
                    st.success("¡Lectura y Discriminado completado!")

        except Exception as e:
            st.error(f"Error técnico (intenta reiniciar): {e}")

st.divider()

# --- FORMULARIO Y FIDELIZACIÓN (Seccion que no se cae) ---
with st.form("registro_mkt", clear_on_submit=False):
    st.subheader("Confirmación y Marketing de Bienvenida")
    
    col1, col2 = st.columns(2)
    with col1:
        nom_form = st.text_input("Nombre", value=st.session_state.get('n_ia', ""))
        tel_form = st.text_input("WhatsApp (10 dígitos)", value=st.session_state.get('t_ia', ""))
    with col2:
        dir_form = st.text_input("Dirección de Entrega", value=st.session_state.get('d_ia', ""))
        promo_mkt = st.selectbox("Estrategia de Fidelización", [
            "Envío GRATIS hoy mismo 🚚",
            "10% de descuento en esta compra 💸",
            "Bono de $5.000 para mañana 🎁"
        ])

    if st.form_submit_button("✅ Guardar Cliente & Enviar Promo"):
        if nom_form and tel_form:
            try:
                fecha_hoy = datetime.now().strftime("%d/%m/%Y")
                # Guardar en DB (INSERT OR REPLACE evita errores de duplicados)
                db.execute("INSERT OR REPLACE INTO clientes (fecha, nombre, direccion, telefono) VALUES (?,?,?,?)", 
                           (fecha_hoy, nom_form, dir_form, tel_form))
                db.commit()
                
                # Mensaje agradable y vendedor
                mensaje_mkt = (f"¡Hola {nom_form}! ✨ Bienvenido a Tropiexpress. Es un placer saludarte. "
                               f"Por tu registro, te activamos: {promo_mkt}. "
                               f"Enviaremos tu pedido a: {dir_form}. ¡Gracias por preferirnos! 🛒")
                
                link_wa = f"https://wa.me/57{tel_form}?text={urllib.parse.quote(mensaje_mkt)}"
                
                st.success(f"¡{nom_form} guardado con éxito!")
                st.markdown(f"### [📲 CLICK AQUÍ PARA WHATSAPP]({link_wa})")
            except Exception as e:
                st.error(f"Error al guardar: {e}")

with tab2:
    st.subheader("Tu Comunidad Tropiexpress")
    if st.button("🔄 Actualizar Tabla"):
        df = pd.read_sql_query("SELECT * FROM clientes ORDER BY id DESC", db)
        st.dataframe(df, use_container_width=True)
