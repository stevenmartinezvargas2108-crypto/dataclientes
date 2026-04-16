import streamlit as st
import pandas as pd
import requests, json, re, base64

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tropiexpress Ultra", layout="wide")
st.title("🚛 Tropiexpress: Centro de Mensajería")

if "db" not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion"])
if "nota_actual" not in st.session_state:
    st.session_state.nota_actual = None

# --- IA CON ESTRUCTURA REFORZADA ---
def procesar_nota_directo(img_bytes):
    try:
        api_key = st.secrets["GEMINI_KEY"].strip()
        # Usamos v1 en lugar de v1beta para mayor estabilidad
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        
        payload = {
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
                    {"text": "Extrae Nombre, Teléfono y Dirección de esta nota. Responde SOLO un JSON: {'nombre': '', 'tel': '', 'dir': ''}"}
                ]
            }],
            "generationConfig": {
                "response_mime_type": "application/json",
            }
        }
        
        res = requests.post(url, json=payload, timeout=30)
        data = res.json()
        
        # Validación de respuesta segura
        if 'candidates' in data and data['candidates'][0]['content']['parts'][0]['text']:
            texto_ia = data['candidates'][0]['content']['parts'][0]['text']
            return json.loads(texto_ia)
        else:
            st.error(f"La IA no pudo leer la imagen. Respuesta: {data}")
            return None
            
    except Exception as e:
        st.error(f"Error técnico: {e}")
        return None

# --- TELEGRAM ---
def capturar_telegram():
    token = st.secrets["TELEGRAM_TOKEN"].strip()
    try:
        url_updates = f"https://api.telegram.org/bot{token}/getUpdates?offset=-1"
        res = requests.get(url_updates, timeout=10).json()
        if res.get("ok") and res.get("result"):
            msg = res["result"][0].get("message", {})
            if "photo" in msg:
                f_id = msg["photo"][-1]["file_id"]
                f_info = requests.get(f"https://api.telegram.org/bot{token}/getFile?file_id={f_id}").json()
                f_path = f_info["result"]["file_path"]
                return requests.get(f"https://api.telegram.org/file/bot{token}/{f_path}").content
    except Exception as e:
        st.sidebar.error(f"Error conexión: {e}")
    return None

# --- INTERFAZ ---
with st.sidebar:
    st.header("⚡ Control")
    if st.button("🔍 CAPTURAR ÚLTIMA NOTA", use_container_width=True):
        with st.spinner("Leyendo Telegram..."):
            img = capturar_telegram()
            if img:
                datos = procesar_nota_directo(img)
                if datos:
                    st.session_state.nota_actual = datos
                    st.success("¡Nota leída con éxito!")
            else:
                st.warning("No hay fotos nuevas en el chat.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Validar Registro")
    if st.session_state.nota_actual:
        with st.form("registro"):
            n = st.text_input("Nombre", st.session_state.nota_actual.get('nombre', ''))
            t = st.text_input("Teléfono", st.session_state.nota_actual.get('tel', ''))
            d = st.text_area("Dirección", st.session_state.nota_actual.get('dir', ''))
            
            if st.form_submit_button("✅ GUARDAR"):
                nuevo = {"Nombre": n, "Telefono": t, "Direccion": d}
                st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([nuevo])], ignore_index=True)
                st.session_state.nota_actual = None
                st.rerun()

with col2:
    st.subheader("📋 Base de Datos")
    st.dataframe(st.session_state.db, use_container_width=True)
