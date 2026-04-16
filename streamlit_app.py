import streamlit as st
import pandas as pd
import json, re, requests, io
from PIL import Image
import google.generativeai as genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tropiexpress Server", layout="wide")
st.title("🚛 Tropiexpress: Gestión de Clientes")

if "db" not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion"])
if "nota_lista" not in st.session_state:
    st.session_state.nota_lista = None

# --- FUNCIÓN DE IA ---
def procesar_con_ia(image_bytes):
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        img = Image.open(io.BytesIO(image_bytes))
        prompt = "Extrae los datos. Responde SOLO JSON: {'nombre':'', 'tel':'', 'dir':''}"
        response = model.generate_content([prompt, img])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group(0))
    except: return None

# --- RECEPTOR DE TELEGRAM ---
# Esta es la pieza que faltaba para que "pase algo" al recibir la foto
def revisar_mensajes_telegram():
    token = st.secrets["TELEGRAM_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        res = requests.get(url, params={"offset": -1, "timeout": 1}).json()
        if res["result"]:
            ultimo_msg = res["result"][0]["message"]
            if "photo" in ultimo_msg:
                file_id = ultimo_msg["photo"][-1]["file_id"]
                # Obtener ruta del archivo
                f_url = f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
                f_path = requests.get(f_url).json()["result"]["file_path"]
                # Descargar imagen
                img_res = requests.get(f"https://api.telegram.org/file/bot{token}/{f_path}")
                return img_res.content
    except: pass
    return None

# --- INTERFAZ ---
with st.sidebar:
    st.subheader("🚀 Control")
    if st.button("🔄 Escanear Telegram ahora"):
        img_bytes = revisar_mensajes_telegram()
        if img_bytes:
            st.session_state.nota_lista = procesar_con_ia(img_bytes)
            st.success("¡Imagen detectada y procesada!")
        else:
            st.warning("No hay fotos nuevas en el chat.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Confirmar Datos")
    if st.session_state.nota_lista:
        with st.form("f_registro"):
            n = st.text_input("Nombre", st.session_state.nota_lista.get('nombre'))
            t = st.text_input("Teléfono", st.session_state.nota_lista.get('tel'))
            d = st.text_area("Dirección", st.session_state.nota_lista.get('dir'))
            if st.form_submit_button("Guardar"):
                # Aquí guardas a tu Excel/Sheets
                st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([{"Nombre":n,"Telefono":t,"Direccion":d}])])
                st.session_state.nota_lista = None
                st.rerun()
    else:
        st.info("Haz clic en 'Escanear Telegram' después de enviar la foto.")

with col2:
    st.subheader("📋 Clientes")
    st.dataframe(st.session_state.db, use_container_width=True)
