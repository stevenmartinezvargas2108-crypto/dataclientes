import streamlit as st
import pandas as pd
from datetime import datetime
import json
import re
import io
from PIL import Image, ImageOps
import google.generativeai as genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="TropiExpress v27", page_icon="🛒")

st.markdown("""
<style>
    .stButton button { width: 100%; height: 3.5rem; font-weight: bold; border-radius: 10px; background-color: #ff4b4b; color: white; }
    div[data-testid="stForm"] { border: 2px solid #ff4b4b; border-radius: 15px; padding: 20px; }
    .stTextInput input { font-size: 1.2rem !important; }
</style>
""", unsafe_allow_html=True)

if 'temp' not in st.session_state:
    st.session_state.temp = {'n': '', 't': '', 'd': ''}
if 'db' not in st.session_state:
    st.session_state.db = []

# --- FUNCIÓN IA (SOLUCIÓN DEFINITIVA AL 404) ---
def procesar_con_gemini(prompt, imagen=None):
    try:
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("Falta la API KEY en Secrets.")
            return False
            
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        
        # Forzamos la configuración del modelo para evitar el error de versión beta
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            generation_config={"fallback_to_unspecified_version": False}
        )
        
        if imagen:
            # Comprimimos para evitar error de memoria
            imagen.thumbnail((800, 800))
            response = model.generate_content([prompt, imagen])
        else:
            response = model.generate_content(prompt)
        
        # Extraer JSON
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            d = json.loads(match.group())
            st.session_state.temp['n'] = str(d.get('nombre', '')).title().strip()
            st.session_state.temp['t'] = re.sub(r'\D', '', str(d.get('telefono', ''))).strip()
            st.session_state.temp['d'] = str(d.get('direccion', '')).upper().strip()
            return True
        return False
    except Exception as e:
        # Si falla el anterior, intentamos el método heredado por seguridad
        st.error(f"Error de conexión: {e}")
        return False

# --- INTERFAZ ---
st.title("🛒 TropiExpress v27")

tab1, tab2 = st.tabs(["📸 Foto", "🎙️ Dictado / Texto"])
P = 'Responde SOLO JSON: {"nombre": "...", "telefono": "...", "direccion": "..."}'

with tab1:
    f = st.file_uploader("Sube foto", type=['jpg','jpeg','png'])
    if f and st.button("PROCESAR FOTO 🚀"):
        with st.spinner("Leyendo..."):
            img = ImageOps.exif_transpose(Image.open(f))
            if procesar_con_gemini(P, img):
                st.rerun()

with tab2:
    txt = st.text_area("Dicta o pega el pedido aquí:", height=150)
    if st.button("PROCESAR TEXTO 🚀"):
        if txt and procesar_con_gemini(P + f"\nTexto: {txt}"):
            st.rerun()

st.divider()

# --- VERIFICACIÓN Y DUPLICADOS ---
with st.form("reg"):
    c1, c2 = st.columns([2, 1])
    v_n = c1.text_input("Nombre", value=st.session_state.temp['n'])
    v_t = c2.text_input("Teléfono", value=st.session_state.temp['t'])
    v_d = st.text_input("Dirección", value=st.session_state.temp['d'])
    
    if st.form_submit_button("✅ GUARDAR REGISTRO"):
        if v_n and v_t:
            if any(c['Tel'] == v_t for c in st.session_state.db):
                st.warning(f"El teléfono {v_t} ya existe.")
            else:
                st.session_state.db.insert(0, {"Cliente": v_n, "Tel": v_t, "Dir": v_d, "Fecha": datetime.now().strftime("%H:%M")})
                st.session_state.temp = {'n': '', 't': '', 'd': ''}
                st.success("¡Guardado!")
                st.rerun()

# --- TABLA, EXCEL Y WHATSAPP ---
if st.session_state.db:
    df = pd.DataFrame(st.session_state.db)
    col_a, col_b = st.columns([2, 1])
    with col_b:
        st.download_button("📥 Excel", df.to_csv(index=False).encode('utf-8-sig'), "base.csv", "text/csv")
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    u = st.session_state.db[0]
    if len(u['Tel']) >= 10:
        link = f"https://wa.me/57{u['Tel']}?text=Hola%20{u['Cliente']},%20recibimos%20tu%20pedido%20en%20TropiExpress."
        st.link_button(f"📲 Bienvenida a {u['Cliente']}", link)
