import streamlit as st
import pandas as pd
from datetime import datetime
import json
import re
import io
from PIL import Image, ImageOps
import google.generativeai as genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="TropiExpress v23 - Light", page_icon="🛒")

st.markdown("""
<style>
    .stButton button { width: 100%; height: 3.5rem; font-weight: bold; border-radius: 10px; }
    div[data-testid="stForm"] { border: 2px solid #ff4b4b; border-radius: 15px; padding: 20px; }
</style>
""", unsafe_allow_html=True)

if 'temp' not in st.session_state:
    st.session_state.temp = {'n': '', 't': '', 'd': ''}
if 'db' not in st.session_state:
    st.session_state.db = []

# --- FUNCIÓN DE COMPRESIÓN (Para evitar error de memoria) ---
def optimizar_imagen(imagen_subida):
    img = Image.open(imagen_subida)
    # Corregir rotación automática
    img = ImageOps.exif_transpose(img)
    # Redimensionar a un tamaño manejable (max 800px)
    img.thumbnail((800, 800), Image.LANCZOS)
    
    # Comprimir en memoria
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=70) # Calidad al 70% es suficiente para IA
    buffer.seek(0)
    return Image.open(buffer)

# --- FUNCIÓN IA ---
def procesar_con_gemini(prompt, imagen_pil=None):
    try:
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("Configura la API KEY en Secrets.")
            return False
            
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        contenido = [prompt, imagen_pil] if imagen_pil else [prompt]
        response = model.generate_content(contenido)
        
        # Extraer JSON de la respuesta
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            datos = json.loads(match.group())
            st.session_state.temp['n'] = str(datos.get('nombre', '')).title().strip()
            st.session_state.temp['t'] = re.sub(r'\D', '', str(datos.get('telefono', ''))).strip()
            st.session_state.temp['d'] = str(datos.get('direccion', '')).upper().strip()
            return True
        return False
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# --- INTERFAZ ---
st.title("🛒 TropiExpress v23")
st.caption("Versión optimizada para bajo consumo de memoria")

t1, t2 = st.tabs(["📸 Foto", "🎙️ Texto"])

PROMPT = 'Extrae en JSON: {"nombre": "...", "telefono": "...", "direccion": "..."}'

with t1:
    archivo = st.file_uploader("Foto del pedido", type=['jpg','jpeg','png'])
    if archivo:
        if st.button("PROCESAR FOTO 🚀"):
            with st.spinner("Optimizando y analizando..."):
                # PASO CRÍTICO: Reducir tamaño antes de enviar a Gemini
                img_ligera = optimizar_imagen(archivo)
                if procesar_con_gemini(PROMPT, img_ligera):
                    st.rerun()

with t2:
    entrada = st.text_area("Dictado o texto:")
    if st.button("PROCESAR TEXTO 🚀"):
        if entrada and procesar_con_gemini(PROMPT + f"\nTexto: {entrada}"):
            st.rerun()

st.divider()

# --- FORMULARIO ---
with st.form("registro"):
    c1, c2 = st.columns([2, 1])
    n = c1.text_input("Nombre", value=st.session_state.temp['n'])
    t = c2.text_input("Teléfono", value=st.session_state.temp['t'])
    d = st.text_input("Dirección", value=st.session_state.temp['d'])
    
    if st.form_submit_button("✅ GUARDAR REGISTRO"):
        if n and t:
            if not any(c['Tel'] == t for c in st.session_state.db):
                st.session_state.db.insert(0, {
                    "Cliente": n, "Tel": t, "Dir": d, 
                    "Hora": datetime.now().strftime("%H:%M")
                })
                st.session_state.temp = {'n': '', 't': '', 'd': ''}
                st.success("¡Guardado!")
                st.rerun()
            else:
                st.warning("Ese teléfono ya existe.")
        else:
            st.error("Faltan datos.")

# --- TABLA Y WHATSAPP ---
if st.session_state.db:
    df = pd.DataFrame(st.session_state.db)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # WhatsApp rápido
    u = st.session_state.db[0]
    num = u['Tel']
    if len(num) >= 10:
        link = f"https://wa.me/57{num}?text=Hola%20{u['Cliente']}%20recibimos%20tu%20pedido."
        st.link_button(f"📲 WhatsApp a {u['Cliente']}", link)
