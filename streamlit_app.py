import streamlit as st
import pandas as pd
import requests, io, json, re
from PIL import Image

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tropiexpress Ultra", layout="wide")
st.title("🚛 Tropiexpress: Centro de Mensajería")

# Inicializar Base de Datos en sesión
if "db" not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion"])
if "nota_actual" not in st.session_state:
    st.session_state.nota_actual = None

# --- NUEVA FUNCIÓN IA (PETICIÓN DIRECTA) ---
def procesar_nota_directo(img_bytes):
    try:
        # Usamos la URL directa de la API para evitar el error 404 de la librería
        api_key = st.secrets["GEMINI_KEY"].strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        import base64
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Extrae de la imagen el nombre, teléfono y dirección. Responde SOLO un JSON así: {'nombre': '', 'tel': '', 'dir': ''}"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                ]
            }]
        }
        
        res = requests.post(url, json=payload, timeout=30).json()
        texto_ia = res['candidates'][0]['content']['parts'][0]['text']
        
        # Limpiar y convertir a diccionario
        match = re.search(r'\{.*\}', texto_ia, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except Exception as e:
        st.error(f"Error crítico en IA: {e}")
        return None

# --- FUNCIÓN TELEGRAM (LIMPIEZA TOTAL) ---
def capturar_telegram():
    # Limpiamos el token de cualquier espacio o salto de línea
    token = st.secrets["TELEGRAM_TOKEN"].strip()
    base_url = f"https://api.telegram.org/bot{token}"
    
    try:
        # 1. Obtener actualizaciones
        updates = requests.get(f"{base_url}/getUpdates?offset=-1", timeout=10).json()
        if updates.get("ok") and updates.get("result"):
            msg = updates["result"][0].get("message", {})
            if "photo" in msg:
                f_id = msg["photo"][-1]["file_id"]
                # 2. Obtener la ruta
                f_info = requests.get(f"{base_url}/getFile?file_id={f_id}").json()
                f_path = f_info["result"]["file_path"]
                # 3. Descarga
                return requests.get(f"https://api.telegram.org/file/bot{token}/{f_path}").content
    except Exception as e:
        st.sidebar.error(f"Error Telegram: {e}")
    return None

# --- INTERFAZ ---
with st.sidebar:
    st.header("⚡ Control")
    if st.button("🔍 CAPTURAR ÚLTIMA NOTA", use_container_width=True):
        with st.spinner("Procesando..."):
            img = capturar_telegram()
            if img:
                datos = procesar_nota_directo(img)
                if datos:
                    st.session_state.nota_actual = datos
                    st.success("¡Datos extraídos!")
            else:
                st.warning("No se encontró ninguna foto nueva.")

# Mostrar formulario y tabla
col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Validar Registro")
    if st.session_state.nota_actual:
        with st.form("registro_cliente"):
            nombre = st.text_input("Nombre", st.session_state.nota_actual.get('nombre', ''))
            tel = st.text_input("Teléfono", st.session_state.nota_actual.get('tel', ''))
            dir = st.text_area("Dirección", st.session_state.nota_actual.get('dir', ''))
            
            if st.form_submit_button("✅ GUARDAR"):
                nuevo = {"Nombre": nombre, "Telefono": tel, "Direccion": dir}
                st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([nuevo])], ignore_index=True)
                st.session_state.nota_actual = None
                st.rerun()
    else:
        st.info("Presiona el botón para procesar una nota de Leidi.")

with col2:
    st.subheader("📋 Base de Datos (Sesión)")
    st.dataframe(st.session_state.db, use_container_width=True)
