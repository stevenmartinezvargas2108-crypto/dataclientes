import streamlit as st
import pandas as pd
from datetime import datetime
import json
import re
from PIL import Image
import google.generativeai as genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="TropiExpress IA v21", page_icon="🛒")

# Estética para móviles
st.markdown("""
<style>
    .stButton button { width: 100%; height: 3rem; font-weight: bold; background-color: #ff4b4b; color: white; }
    .stTextInput input { font-size: 1.1rem; }
    div[data-testid="stForm"] { border: 2px solid #ff4b4b; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'temp' not in st.session_state:
    st.session_state.temp = {'n': '', 't': '', 'd': ''}
if 'db' not in st.session_state:
    st.session_state.db = []

# --- CONEXIÓN IA ---
def procesar_con_gemini(prompt, imagen=None):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Si hay imagen, enviamos imagen + prompt, si no, solo texto
        contenido = [prompt, imagen] if imagen else [prompt]
        response = model.generate_content(contenido)
        
        # Limpiar respuesta JSON
        res_text = response.text.replace('```json', '').replace('```', '').strip()
        datos = json.loads(res_text)
        
        st.session_state.temp['n'] = str(datos.get('nombre', '')).title().strip()
        st.session_state.temp['t'] = re.sub(r'\D', '', str(datos.get('telefono', ''))).strip()
        st.session_state.temp['d'] = str(datos.get('direccion', '')).upper().strip()
        return True
    except Exception as e:
        st.error(f"Error de IA: {e}")
        return False

# --- INTERFAZ ---
st.title("🛒 TropiExpress IA Vision")

t1, t2 = st.tabs(["📸 Foto Directa", "🎙️ Dictado / Texto"])

# Prompt maestro para Gemini
PROMPT_EXTRACTOR = """
Analiza la información y extrae: nombre del cliente, teléfono y dirección.
Responde ÚNICAMENTE en este formato JSON:
{"nombre": "...", "telefono": "...", "direccion": "..."}
Si no encuentras un dato, deja el valor vacío "".
"""

with t1:
    foto = st.file_uploader("Sube o toma foto de la nota", type=['jpg','png','jpeg'])
    if foto and st.button("LEER FOTO CON IA 🚀"):
        img = Image.open(foto)
        with st.spinner("Gemini analizando imagen..."):
            if procesar_con_gemini(PROMPT_EXTRACTOR, img):
                st.rerun()

with t2:
    entrada = st.text_area("Pega texto o usa el dictado del teclado:")
    if st.button("PROCESAR TEXTO 🚀"):
        if entrada:
            with st.spinner("Procesando texto..."):
                if procesar_con_gemini(PROMPT_EXTRACTOR + f"\nTexto: {entrada}"):
                    st.rerun()

st.divider()

# --- VERIFICACIÓN Y GUARDADO ---
st.subheader("📝 Verificación de Datos")
with st.form("valida"):
    f_nom = st.text_input("Nombre", value=st.session_state.temp['n'])
    f_tel = st.text_input("Teléfono", value=st.session_state.temp['t'])
    f_dir = st.text_input("Dirección", value=st.session_state.temp['d'])
    
    if st.form_submit_button("✅ GUARDAR EN BASE DE DATOS"):
        if f_nom and f_tel:
            # Check Duplicados
            existe = any(cliente['Tel'] == f_tel for cliente in st.session_state.db)
            if existe:
                st.warning(f"⚠️ El teléfono {f_tel} ya está registrado.")
            else:
                nuevo = {
                    "Cliente": f_nom, "Tel": f_tel, "Dir": f_dir, 
                    "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                st.session_state.db.insert(0, nuevo)
                st.session_state.temp = {'n': '', 't': '', 'd': ''} # Limpiar
                st.success("¡Guardado!")
                st.rerun()
        else:
            st.error("Nombre y Teléfono son obligatorios.")

# --- BASE DE DATOS Y WHATSAPP ---
if st.session_state.db:
    st.divider()
    df = pd.DataFrame(st.session_state.db)
    
    col_a, col_b = st.columns([2,1])
    with col_a:
        st.subheader("📋 Registros")
    with col_b:
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Descargar Excel (CSV)", csv, "clientes_tropiexpress.csv", "text/csv")

    st.dataframe(df, use_container_width=True, hide_index=True)

    # Botón de WhatsApp para el último registro
    ultimo = st.session_state.db[0]
    tel_wa = ultimo['Tel']
    if len(tel_wa) >= 10:
        if not tel_wa.startswith("57"): tel_wa = "57" + tel_wa
        msg = f"Hola {ultimo['Cliente']}, bienvenido a TropiExpress. Hemos recibido tu pedido."
        link = f"https://wa.me/{tel_wa}?text={msg.replace(' ', '%20')}"
        st.link_button(f"📲 Enviar Bienvenida a {ultimo['Cliente']}", link)
