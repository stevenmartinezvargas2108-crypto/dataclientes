import streamlit as st
import cv2
import numpy as np
import easyocr
import re
import urllib.parse
from PIL import Image

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tropiexpress Ultra-Scanner", page_icon="🛒")

if 'mkt_data' not in st.session_state:
    st.session_state['mkt_data'] = {'n': '', 't': '', 'd': ''}

@st.cache_resource
def get_reader():
    return easyocr.Reader(['es'], gpu=False)

def procesar_imagen_quirurgica(image_pil):
    # 1. Redimensionar para no colgar el servidor
    img = np.array(image_pil.convert('RGB'))
    img = cv2.resize(img, (1100, int(img.shape[0] * (1100 / img.shape[1]))))
    
    # 2. Eliminar el ruido del papel (Blanqueo extremo)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # Filtro para resaltar el lapicero sobre el papel crema
    rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, rect_kernel)
    _, thresh = cv2.threshold(blackhat, 10, 255, cv2.THRESH_BINARY_INV)
    
    return thresh

# --- INTERFAZ ---
st.title("🛒 Tropiexpress: Escáner Inteligente")

archivo = st.file_uploader("Sube la foto del pedido", type=['jpg', 'jpeg', 'png'])

if archivo:
    img_pil = Image.open(archivo)
    img_prep = procesar_imagen_quirurgica(img_pil)
    st.image(img_prep, caption="Vista de alta definición", width=400)

    if st.button("🚀 EXTRAER DATOS (MODO PRECISIÓN)"):
        with st.spinner("Analizando manuscrito..."):
            reader = get_reader()
            # Escaneo con ajuste de contraste interno
            results = reader.readtext(img_prep, detail=0, paragraph=True, min_size=10)
            
            if results:
                full_text = " ".join(results).lower()
                
                # --- LÓGICA DE DISCRIMINACIÓN TIPO HUMANO ---
                # 1. Celular: Buscamos 10 dígitos que empiecen por 3
                nums_only = re.sub(r'\D', '', full_text)
                tel_match = re.search(r'3\d{9}', nums_only)
                
                # 2. Dirección: Buscamos palabras clave de vías en Medellín
                keywords_dir = ['calle', 'cll', 'cra', 'carrera', 'trans', 'trv', '#', 'no', 'nro', 'apto', 'casa', 'piso']
                direccion = ""
                for res in results:
                    if any(key in res.lower() for key in keywords_dir) and any(char.isdigit() for char in res):
                        direccion = res
                        break
                
                # 3. Nombre: Si no es dirección ni teléfono, y está al principio, es el nombre
                nombre = results[0]
                for res in results:
                    if len(res) > 5 and not any(key in res.lower() for key in keywords_dir) and not re.search(r'3\d{9}', res):
                        nombre = res
                        break

                st.session_state['mkt_data'] = {
                    'n': nombre.title(),
                    't': tel_match.group() if tel_match else "",
                    'd': direccion.title()
                }
                st.success("¡Datos capturados con éxito!")

st.divider()

# --- FORMULARIO DE FIDELIZACIÓN ---
with st.form("registro_tropi"):
    c1, c2 = st.columns(2)
    with c1:
        n_input = st.text_input("Nombre", value=st.session_state['mkt_data']['n'])
        t_input = st.text_input("Celular", value=st.session_state['mkt_data']['t'])
    with c2:
        d_input = st.text_input("Dirección", value=st.session_state['mkt_data']['d'])
        promo = st.selectbox("Incentivo", ["Envío Gratis 🚚", "Bono $5.000 🎁"])

    if st.form_submit_button("✅ GUARDAR Y ENVIAR BIENVENIDA"):
        if n_input and t_input:
            msg = f"Hola {n_input}, bienvenido a Tropiexpress. Promo: {promo}. Destino: {d_input}"
            link = f"https://wa.me/57{t_input}?text={urllib.parse.quote(msg)}"
            st.markdown(f"### [📲 CLICK AQUÍ PARA WHATSAPP]({link})")
