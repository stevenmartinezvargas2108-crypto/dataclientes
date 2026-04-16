import streamlit as st
import pandas as pd
import json, re, requests, io
from PIL import Image
import google.generativeai as genai

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="Tropiexpress Ultra", layout="wide", page_icon="🚛")
st.title("🚛 Tropiexpress: Centro de Mensajería")

if "db" not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion"])
if "nota_actual" not in st.session_state:
    st.session_state.nota_actual = None

# --- FUNCIÓN DE IA (CORRECCIÓN ERROR 404) ---
def procesar_nota_ia(img_bytes):
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        
        # Intentamos con el nombre técnico completo que es el más compatible
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest') 
        
        img = Image.open(io.BytesIO(img_bytes))
        prompt = "Extrae Nombre, Teléfono y Dirección de la nota. Responde SOLO un JSON: {'nombre':'', 'tel':'', 'dir':''}"
        
        response = model.generate_content([prompt, img])
        
        # Limpieza profunda de la respuesta
        res_text = response.text.replace('json', '').replace('', '').strip()
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        
        return json.loads(match.group(0)) if match else None
    except Exception as e:
        st.error(f"Error IA: {e}")
        return None

# --- FUNCIÓN TELEGRAM (CORRECCIÓN ADAPTERS) ---
def capturar_desde_telegram():
    # El .strip() elimina espacios accidentales que causan el error de conexión
    token = st.secrets["TELEGRAM_TOKEN"].strip()
    base_url = f"https://api.telegram.org/bot{token}"
    
    try:
        # 1. Obtener última actualización
        updates = requests.get(f"{base_url}/getUpdates?offset=-1", timeout=10).json()
        if updates.get("ok") and updates.get("result"):
            msg = updates["result"][0].get("message", {})
            if "photo" in msg:
                file_id = msg["photo"][-1]["file_id"]
                # 2. Obtener ruta del archivo
                f_info = requests.get(f"{base_url}/getFile?file_id={file_id}").json()
                f_path = f_info["result"]["file_path"]
                # 3. Descargar imagen
                return requests.get(f"https://api.telegram.org/file/bot{token}/{f_path}").content
    except Exception as e:
        st.sidebar.error(f"Error de conexión: {e}")
    return None

# --- INTERFAZ ---
with st.sidebar:
    st.header("⚡ Acciones")
    if st.button("🔍 CAPTURAR ÚLTIMA NOTA", use_container_width=True):
        with st.spinner("Leyendo Telegram..."):
            img_data = capturar_desde_telegram()
            if img_data:
                resultado = procesar_nota_ia(img_data)
                if resultado:
                    st.session_state.nota_actual = resultado
                    st.success("¡Nota encontrada!")
            else:
                st.warning("No hay fotos nuevas.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Validar e Ingresar")
    if st.session_state.nota_actual:
        with st.form("registro"):
            # Precarga los datos de Leidi o el cliente que envíes
            n = st.text_input("Nombre", st.session_state.nota_actual.get('nombre', ''))
            t = st.text_input("Teléfono", st.session_state.nota_actual.get('tel', ''))
            d = st.text_area("Dirección", st.session_state.nota_actual.get('dir', ''))
            
            if st.form_submit_button("✅ GUARDAR"):
                nuevo = {"Nombre": n, "Telefono": t, "Direccion": d}
                st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([nuevo])], ignore_index=True)
                st.session_state.nota_actual = None
                st.rerun()
    else:
        st.info("Presiona 'Capturar' para procesar la foto.")

with col2:
    st.subheader("📋 Historial")
    st.dataframe(st.session_state.db, use_container_width=True)
