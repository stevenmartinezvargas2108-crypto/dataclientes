import streamlit as st
import pandas as pd
import json, re, requests, io
from PIL import Image
import google.generativeai as genai

st.set_page_config(page_title="Tropiexpress Ultra", layout="wide")
st.title("🚛 Tropiexpress: Nodo de Extracción")

# --- BASE DE DATOS LOCAL ---
if "db" not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion"])
if "nota_actual" not in st.session_state:
    st.session_state.nota_actual = None

# --- FUNCIÓN IA ---
def procesar_nota(img_bytes):
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        img = Image.open(io.BytesIO(img_bytes))
        prompt = "Extrae Nombre, Tel y Dir. Responde SOLO JSON: {'nombre':'', 'tel':'', 'dir':''}"
        response = model.generate_content([prompt, img])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group(0))
    except Exception as e:
        st.error(f"Error IA: {e}")
        return None

# --- FUNCIÓN TELEGRAM (POLLING) ---
def buscar_en_telegram():
    token = st.secrets["TELEGRAM_TOKEN"]
    # Usamos un offset de 0 para revisar el historial disponible
    url = f"https://api.telegram.org/bot{token}/getUpdates?limit=10"
    try:
        res = requests.get(url).json()
        if res["ok"] and res["result"]:
            # Buscamos la foto más reciente en los últimos 10 mensajes
            for item in reversed(res["result"]):
                msg = item.get("message", {})
                if "photo" in msg:
                    file_id = msg["photo"][-1]["file_id"]
                    f_info = requests.get(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}").json()
                    f_path = f_info["result"]["file_path"]
                    return requests.get(f"https://api.telegram.org/file/bot{token}/{f_path}").content
    except: pass
    return None

# --- INTERFAZ ---
with st.sidebar:
    st.header("⚡ Acciones")
    if st.button("🔍 CAPTURAR ÚLTIMA NOTA", use_container_width=True):
        with st.spinner("Conectando con Telegram..."):
            img_bytes = buscar_en_telegram()
            if img_bytes:
                st.session_state.nota_actual = procesar_nota(img_bytes)
                st.success("¡Nota encontrada!")
            else:
                st.warning("No vi fotos nuevas. Reenvía la imagen al bot y pulsa de nuevo.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Validar Información")
    if st.session_state.nota_actual:
        with st.form("validador"):
            nom = st.text_input("Nombre", st.session_state.nota_actual.get('nombre'))
            tel = st.text_input("Teléfono", st.session_state.nota_actual.get('tel'))
            dir = st.text_area("Dirección", st.session_state.nota_actual.get('dir'))
            
            if st.form_submit_button("💾 GUARDAR CLIENTE"):
                # Simulación de guardado
                nuevo = {"Nombre": nom, "Telefono": tel, "Direccion": dir}
                st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([nuevo])], ignore_index=True)
                st.session_state.nota_actual = None
                st.rerun()
    else:
        st.info("Esperando captura de Telegram...")

with col2:
    st.subheader("✅ Clientes Registrados")
    st.dataframe(st.session_state.db, use_container_width=True)
