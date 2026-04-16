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

# --- IA: VERSIÓN ULTRA-COMPATIBLE ---
def procesar_nota_directo(img_bytes):
    try:
        api_key = st.secrets["GEMINI_KEY"].strip()
        # Regresamos a v1beta que es más flexible con esquemas de respuesta
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        
        # Eliminamos 'generationConfig' para evitar el error de campo desconocido
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Extrae de la imagen: nombre, tel y dir. Responde SOLO un JSON: {'nombre':'', 'tel':'', 'dir':''}"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                ]
            }]
        }
        
        res = requests.post(url, json=payload, timeout=30)
        data = res.json()
        
        if 'candidates' in data:
            texto_ia = data['candidates'][0]['content']['parts'][0]['text']
            # Limpieza manual por si la IA agrega texto extra
            match = re.search(r'\{.*\}', texto_ia, re.DOTALL)
            return json.loads(match.group(0)) if match else None
        else:
            st.error(f"Error en respuesta: {data}")
            return None
            
    except Exception as e:
        st.error(f"Error técnico: {e}")
        return None

# --- TELEGRAM ---
def capturar_telegram():
    token = st.secrets["TELEGRAM_TOKEN"].strip()
    try:
        base = f"https://api.telegram.org/bot{token}"
        res = requests.get(f"{base}/getUpdates?offset=-1", timeout=10).json()
        if res.get("ok") and res.get("result"):
            msg = res["result"][0].get("message", {})
            if "photo" in msg:
                f_id = msg["photo"][-1]["file_id"]
                f_info = requests.get(f"{base}/getFile?file_id={f_id}").json()
                f_path = f_info["result"]["file_path"]
                return requests.get(f"https://api.telegram.org/file/bot{token}/{f_path}").content
    except Exception as e:
        st.sidebar.error(f"Error Telegram: {e}")
    return None

# --- INTERFAZ ---
with st.sidebar:
    st.header("⚡ Control")
    if st.button("🔍 CAPTURAR ÚLTIMA NOTA", use_container_width=True):
        with st.spinner("Procesando nota..."):
            img = capturar_telegram()
            if img:
                datos = procesar_nota_directo(img)
                if datos:
                    st.session_state.nota_actual = datos
                    st.success("¡Nota procesada!")
            else:
                st.warning("No hay fotos nuevas.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Validar Registro")
    if st.session_state.nota_actual:
        with st.form("form_registro"):
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
