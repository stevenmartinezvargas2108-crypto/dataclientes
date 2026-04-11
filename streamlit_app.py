import streamlit as st
import sqlite3
import pandas as pd
import easyocr
import numpy as np
import cv2
from PIL import Image
import re
from datetime import datetime

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Tropiexpress Pro", page_icon="🚀", layout="centered")
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('tropiexpress_marketing.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, direccion TEXT, telefono TEXT UNIQUE)''')
    return conn

@st.cache_resource
def load_ocr():
    # Modelo refinado para español
    return easyocr.Reader(['es'], gpu=False)

db = init_db()
reader = load_ocr()

# --- FUNCIONES DE MEJORA DE IMAGEN (Para mejorar la extracción) ---
def mejorar_imagen_para_ocr(image):
    # Convertir a arreglo para OpenCV
    img_array = np.array(image.convert('RGB'))
    img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # 1. Escala de grises
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # 2. Eliminar sombras y resaltar texto (Umbral adaptativo)
    # Esto ayuda cuando el papel tiene arrugas o sombras
    processed = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # 3. Reducción de ruido (Denoising)
    processed = cv2.medianBlur(processed, 3)
    
    return processed

# --- INTERFAZ DE USUARIO ---
st.title("🚀 Tropiexpress Marketing Pro")
st.write("Registra clientes y fideliza con promociones automáticas.")

tab1, tab2 = st.tabs(["📲 Registro & Venta", "📊 Base de Datos"])

with tab1:
    foto = st.camera_input("Capturar datos del cliente") # Directo a la cámara para mejor enfoque
    
    if foto:
        img_original = Image.open(foto)
        img_ia = mejorar_imagen_para_ocr(img_original)
        
        st.image(img_ia, caption="Escáner Pro activo", width=300)
        
        if st.button("🔍 Extraer Datos con IA"):
            with st.spinner("Analizando texto..."):
                # Leer la imagen procesada
                resultados = reader.readtext(img_ia)
                texto_sucio = " ".join([res[1] for res in resultados])
                
                # Búsqueda agresiva de teléfono (10 dígitos)
                nums = re.sub(r'[^0-9]', '', texto_sucio)
                tel_encontrado = re.search(r'\d{10}', nums)
                
                st.session_state['n_ia'] = resultados[0][1] if resultados else ""
                st.session_state['t_ia'] = tel_encontrado.group() if tel_encontrado else ""
                st.session_state['d_ia'] = "" # La dirección suele requerir ajuste manual

    # FORMULARIO DE REGISTRO
    with st.form("form_marketing", clear_on_submit=False):
        st.subheader("Confirmación de Cliente")
        col1, col2 = st.columns(2)
        
        with col1:
            nombre = st.text_input("Nombre", value=st.session_state.get('n_ia', ""))
            whatsapp = st.text_input("WhatsApp", value=st.session_state.get('t_ia', ""))
        with col2:
            direccion = st.text_input("Dirección", value=st.session_state.get('d_ia', ""))
            promo = st.selectbox("Estrategia de Atracción", [
                "10% Descuento Primera Compra",
                "Envío Gratis en este pedido",
                "Bono de $5.000 para mañana",
                "Sin promoción"
            ])

        if st.form_submit_button("✅ Guardar y Fidelizar Cliente"):
            if nombre and whatsapp:
                try:
                    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
                    db.execute("INSERT INTO clientes (fecha, nombre, direccion, telefono) VALUES (?,?,?,?)",
                               (fecha_hoy, nombre, direccion, whatsapp))
                    db.commit()
                    st.success(f"¡{nombre} ha sido registrado!")
                except:
                    db.execute("UPDATE clientes SET nombre=?, direccion=? WHERE telefono=?",
                               (nombre, direccion, whatsapp))
                    db.commit()
                    st.info("Datos de cliente frecuente actualizados.")

                # ESTRATEGIA DE MARKETING EN WHATSAPP
                # Mensaje agradable y vendedor
                mensaje_mkt = (
                    f"¡Hola {nombre}! ✨ Bienvenido a la familia *Tropiexpress*. "
                    f"Es un placer saludarte. 🛒\n\n"
                    f"Como eres especial para nosotros, te hemos asignado: *{promo}*. 🎁\n\n"
                    f"Tu pedido será enviado a: _{direccion}_. "
                    f"¡Gracias por elegirnos y hacernos parte de tu día!"
                )
                
                # Codificar enlace
                link_wa = f"https://wa.me/57{whatsapp}?text={mensaje_mkt.replace(' ', '%20').replace('\n', '%0A')}"
                st.markdown(f"### [📲 ENVIAR PROMOCIÓN POR WHATSAPP]({link_wa})")

with tab2:
    st.subheader("Tu Comunidad de Clientes")
    df = pd.read_sql_query("SELECT * FROM clientes", db)
    st.dataframe(df, use_container_width=True)
    
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Base para Campañas", data=csv, file_name="mkt_tropiexpress.csv")
