import streamlit as st
import pandas as pd
import json, re, requests, io
from PIL import Image
import google.generativeai as genai

# Configuración básica
st.set_page_config(page_title="Tropiexpress Ultra", layout="wide", page_icon="🚛")
st.title("🚛 Tropiexpress: Centro de Mensajería")

# Inicialización de datos
if "db" not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion"])
if "nota_actual" not in st.session_state:
    st.session_state.nota_actual = None

def procesar_nota_ia(img_bytes):
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        # Nombre técnico exacto para evitar el error 404
        model = genai.GenerativeModel('gemini-1.5-flash') 
        
        img = Image.open(io.BytesIO(img_bytes))
        prompt = "Extrae Nombre, Teléfono y Dirección de esta nota. Responde SOLO el JSON: {'nombre': '', 'tel': '', 'dir': ''}"
        
        response = model.generate_content([prompt, img])
        # Limpieza de la respuesta para obtener solo el JSON
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except Exception as e:
        st.error(f"Error IA: {e}")
        return None

def capturar_desde_telegram():
    # Limpiamos el token de cualquier espacio accidental
    token = st.secrets["TELEGRAM_TOKEN"].strip()
    # Construcción ultra-segura de la URL
    url = f"https://api.telegram.org/bot{token}/getUpdates?offset=-1"
    
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("ok") and res.get("result"):
            msg = res["result"][0].get("message", {})
            if "photo" in msg:
                file_id = msg["photo"][-1]["file_id"]
                # Obtener la ruta del archivo
                file_url = f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
                f_info = requests.get(file_url).json()
                f_path = f_info["result"]["file_path"]
                # Descarga final
                download_url = f"https://api.telegram.org/file/bot{token}/{f_path}"
                return requests.get(download_url).content
    except Exception as e:
        st.sidebar.error(f"Error de conexión: {e}")
    return None

# --- Interfaz de Usuario ---
with st.sidebar:
    st.header("⚡ Acciones")
    if st.button("🔍 CAPTURAR ÚLTIMA NOTA", use_container_width=True):
        with st.spinner("Buscando en Telegram..."):
            img_data = capturar_desde_telegram()
            if img_data:
                resultado = procesar_nota_ia(img_data)
                if resultado:
                    st.session_state.nota_actual = resultado
                    st.success("¡Nota encontrada!")
            else:
                st.warning("No hay fotos nuevas en el chat.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Validar Datos")
    if st.session_state.nota_actual:
        with st.form("validador"):
            n = st.text_input("Nombre", st.session_state.nota_actual.get('nombre', ''))
            t = st.text_input("Teléfono", st.session_state.nota_actual.get('tel', ''))
            d = st.text_area("Dirección", st.session_state.nota_actual.get('dir', ''))
            
            if st.form_submit_button("✅ GUARDAR CLIENTE"):
                nuevo = {"Nombre": n, "Telefono": t, "Direccion": d}
                st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([nuevo])], ignore_index=True)
                st.session_state.nota_actual = None
                st.rerun()
    else:
        st.info("Usa el botón de la izquierda para procesar una nota.")

with col2:
    st.subheader("📋 Clientes Registrados")
    st.dataframe(st.session_state.db, use_container_width=True)
