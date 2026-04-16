import streamlit as st
import pandas as pd
import json, re, requests, io
from PIL import Image
import google.generativeai as genai

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress Ultra", layout="wide", page_icon="🚛")
st.title("🚛 Tropiexpress: Centro de Mensajería")

# --- INICIALIZACIÓN DE MEMORIA ---
if "db" not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=["Nombre", "Telefono", "Direccion"])
if "nota_actual" not in st.session_state:
    st.session_state.nota_actual = None

# --- FUNCIÓN DE INTELIGENCIA ARTIFICIAL ---
def procesar_nota_ia(img_bytes):
    try:
        # Configuración con tu llave secreta
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        
        # ACTUALIZACIÓN: Nombre de modelo corregido para evitar error 404
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest') 
        
        img = Image.open(io.BytesIO(img_bytes))
        prompt = """
        Analiza esta nota de entrega. 
        Extrae el Nombre del cliente, su Teléfono y la Dirección completa.
        Responde ÚNICAMENTE en formato JSON puro:
        {"nombre": "", "tel": "", "dir": ""}
        """
        
        response = model.generate_content([prompt, img])
        
        # Limpieza de markdown (por si la IA responde con json ...)
        texto_limpio = response.text.replace('json', '').replace('```', '').strip()
        
        # Buscar el JSON dentro del texto
        match = re.search(r'\{.*\}', texto_limpio, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
        
    except Exception as e:
        st.error(f"Error en el procesamiento de IA: {e}")
        return None

# --- FUNCIÓN DE CONEXIÓN CON TELEGRAM ---
def capturar_desde_telegram():
    token = st.secrets["TELEGRAM_TOKEN"]
    # Consultamos los últimos mensajes (polling)
    url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){token}/getUpdates?offset=-1"
    try:
        res = requests.get(url, timeout=5).json()
        if res["ok"] and res["result"]:
            msg = res["result"][0].get("message", {})
            if "photo" in msg:
                # Obtenemos la foto de mejor resolución
                file_id = msg["photo"][-1]["file_id"]
                f_info = requests.get(f"[https://api.telegram.org/bot](https://api.telegram.org/bot){token}/getFile?file_id={file_id}").json()
                f_path = f_info["result"]["file_path"]
                # Descargamos los bytes de la imagen
                return requests.get(f"[https://api.telegram.org/file/bot](https://api.telegram.org/file/bot){token}/{f_path}").content
    except Exception as e:
        st.sidebar.error(f"Error Telegram: {e}")
    return None

# --- DISEÑO DE LA INTERFAZ ---
with st.sidebar:
    st.header("⚡ Acciones")
    if st.button("🔍 CAPTURAR ÚLTIMA NOTA", use_container_width=True):
        with st.spinner("Buscando foto de Leidi en Telegram..."):
            img_data = capturar_desde_telegram()
            if img_data:
                resultado = procesar_nota_ia(img_data)
                if resultado:
                    st.session_state.nota_actual = resultado
                    st.success("¡Nota encontrada y leída!")
                else:
                    st.error("No se pudo interpretar la nota.")
            else:
                st.warning("No hay fotos nuevas en el chat.")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Validar e Ingresar")
    if st.session_state.nota_actual:
        # Formulario con los datos precargados por la IA
        with st.form("registro_cliente"):
            nombre_edit = st.text_input("Nombre", st.session_state.nota_actual.get('nombre', ''))
            tel_edit = st.text_input("Teléfono", st.session_state.nota_actual.get('tel', ''))
            dir_edit = st.text_area("Dirección", st.session_state.nota_actual.get('dir', ''))
            
            if st.form_submit_button("✅ GUARDAR EN BASE DE DATOS"):
                # Crear nuevo registro
                nuevo_dato = {
                    "Nombre": nombre_edit, 
                    "Telefono": tel_edit, 
                    "Direccion": dir_edit
                }
                # Guardar en el DataFrame de la sesión
                st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([nuevo_dato])], ignore_index=True)
                st.session_state.nota_actual = None # Limpiar para la siguiente
                st.balloons()
                st.rerun()
    else:
        st.info("Reenvía la foto al bot de Telegram y presiona el botón de 'Capturar'.")

with col2:
    st.subheader("📋 Registro de Hoy")
    st.dataframe(st.session_state.db, use_container_width=True)
    
    if not st.session_state.db.empty:
        # Botón para descargar lo que lleves registrado
        csv = st.session_state.db.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Excel (CSV)", data=csv, file_name="clientes_tropiexpress.csv")
