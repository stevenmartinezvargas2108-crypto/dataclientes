import streamlit as st
import sqlite3
import pandas as pd
import easyocr
import numpy as np
import cv2
from PIL import Image
import re
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tropiexpress Master", page_icon="🛒")

if 'temp_datos' not in st.session_state:
    st.session_state['temp_datos'] = {'n': '', 't': '', 'd': ''}

@st.cache_resource
def cargar_lector():
    return easyocr.Reader(['es'], gpu=False)

def limpiar_imagen_top(image_pil):
    # Reducir para que el servidor no se cuelgue por tiempo
    img_np = np.array(image_pil.convert('RGB'))
    img_cv = cv2.resize(img_np, (1000, int(img_np.shape[0] * (1000 / img_np.shape[1]))))
    gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    # Filtro para eliminar el gris del papel y resaltar la tinta
    img_final = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return img_final

# --- INTERFAZ ---
st.title("🛒 Tropiexpress: Extractor Inteligente")

archivo = st.file_uploader("Sube la foto del pedido", type=['jpg', 'jpeg', 'png'])

if archivo:
    img_pil = Image.open(archivo)
    img_procesada = limpiar_imagen_top(img_pil)
    st.image(img_procesada, caption="Imagen optimizada", width=350)

    if st.button("🚀 EXTRAER DATOS COMO EXPERTO"):
        with st.spinner("Analizando información..."):
            reader = cargar_lector()
            # Leemos con 'paragraph=True' para que no rompa las direcciones largas
            resultados = reader.readtext(img_procesada, detail=0, paragraph=True)
            
            if resultados:
                texto_sucio = " ".join(resultados).replace("\n", " ")
                
                # 1. EXTRAER TELÉFONO (Busca 10 números que inicien con 3)
                numeros = re.sub(r'\D', '', texto_sucio)
                tel_match = re.search(r'3\d{9}', numeros)
                
                # 2. EXTRAER DIRECCIÓN (Busca palabras clave de vías)
                patron_dir = re.compile(r'(calle|cll|cra|carrera|transversal|trv|diagonal|diag|#|nro|no|casa|apto|piso|interior|sector|manzana|mz)', re.I)
                direccion = ""
                for bloque in resultados:
                    if patron_dir.search(bloque):
                        direccion = bloque.strip()
                        break
                
                # 3. EXTRAER NOMBRE (Suele ser el primer bloque que no es dirección)
                nombre = resultados[0]
                for bloque in resultados:
                    if "nombre" in bloque.lower():
                        nombre = bloque.lower().replace("nombre", "").replace(":", "").replace("=", "").strip()
                        break
                    elif len(bloque) > 3 and not patron_dir.search(bloque) and not any(char.isdigit() for char in bloque[:3]):
                        nombre = bloque
                        break

                st.session_state['temp_datos'] = {
                    'n': nombre.title(),
                    't': tel_match.group() if tel_match else "",
                    'd': direccion.title()
                }
                st.success("¡Datos capturados!")

st.divider()

# --- FORMULARIO FINAL ---
with st.form("registro_tropi"):
    c1, c2 = st.columns(2)
    with c1:
        nom_f = st.text_input("Nombre", value=st.session_state['temp_datos']['n'])
        tel_f = st.text_input("WhatsApp", value=st.session_state['temp_datos']['t'])
    with c2:
        dir_f = st.text_input("Dirección", value=st.session_state['temp_datos']['d'])
        promo = st.selectbox("Regalo", ["Envío Gratis 🚚", "Bono $5.000 🎁"])

    if st.form_submit_button("✅ GUARDAR Y ENVIAR"):
        if nom_f and tel_f:
            conn = sqlite3.connect('tropiexpress_data.db')
            conn.execute("INSERT OR REPLACE INTO clientes (nombre, direccion, telefono) VALUES (?,?,?)", (nom_f, dir_f, tel_f))
            conn.commit()
            
            # Enlace de WhatsApp sin errores de sintaxis
            txt = f"Hola {nom_f}, bienvenido a Tropiexpress. Tu promo: {promo}. Pedido para: {dir_f}"
            link = f"https://wa.me/57{tel_f}?text={urllib.parse.quote(txt)}"
            st.markdown(f"### [📲 CLICK PARA WHATSAPP]({link})")
