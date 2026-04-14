import streamlit as st
import pandas as pd
from datetime import datetime
import json
import re
import io
from PIL import Image, ImageOps
import google.generativeai as genai

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TropiExpress v26 - Full", page_icon="🛒", layout="centered")

# Estilo para botones grandes y legibles en móvil
st.markdown("""
<style>
    .stButton button { width: 100%; height: 3.5rem; font-weight: bold; border-radius: 10px; background-color: #ff4b4b; color: white; }
    div[data-testid="stForm"] { border: 2px solid #ff4b4b; border-radius: 15px; padding: 20px; background-color: white; }
    .stTextInput input { font-size: 1.2rem !important; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE ESTADOS ---
if 'temp' not in st.session_state:
    st.session_state.temp = {'n': '', 't': '', 'd': ''}
if 'db' not in st.session_state:
    st.session_state.db = []

# --- FUNCIÓN IA (CORRECCIÓN ERROR 404 Y MEMORIA) ---
def procesar_con_gemini(prompt_instrucciones, imagen_pil=None):
    try:
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("⚠️ Configura GEMINI_API_KEY en los Secrets de Streamlit.")
            return False
            
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        
        # Intentamos con el nombre que NO da error 404
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        if imagen_pil:
            # Reducimos tamaño para evitar error de memoria en el envío
            imagen_pil.thumbnail((800, 800))
            response = model.generate_content([prompt_instrucciones, imagen_pil])
        else:
            response = model.generate_content(prompt_instrucciones)
        
        # Extraer JSON de la respuesta de la IA
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            datos = json.loads(match.group())
            st.session_state.temp['n'] = str(datos.get('nombre', '')).title().strip()
            st.session_state.temp['t'] = re.sub(r'\D', '', str(datos.get('telefono', ''))).strip()
            st.session_state.temp['d'] = str(datos.get('direccion', '')).upper().strip()
            return True
        return False
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return False

# --- INTERFAZ PRINCIPAL ---
st.title("🛒 TropiExpress v26")
st.info("Captura pedidos y organiza tu base de datos automáticamente.")

tab_foto, tab_voz = st.tabs(["📸 Subir Foto", "🎙️ Dictado / Texto"])

PROMPT_MAESTRO = 'Extrae los datos y responde SOLO en este formato JSON: {"nombre": "...", "telefono": "...", "direccion": "..."}'

with tab_foto:
    f = st.file_uploader("Sube foto de la nota", type=['jpg','jpeg','png'])
    if f and st.button("PROCESAR FOTO 🚀"):
        with st.spinner("Analizando imagen..."):
            img = Image.open(f)
            img = ImageOps.exif_transpose(img) # Corrige rotación de celular
            if procesar_con_gemini(PROMPT_MAESTRO, img):
                st.success("¡Datos extraídos con éxito!")
                st.rerun()

with tab_voz:
    st.write("Usa el micrófono de tu teclado para dictar:")
    texto_entrada = st.text_area("Pega o dicta el pedido aquí:", height=150)
    if st.button("PROCESAR DICTADO 🚀"):
        if texto_entrada:
            with st.spinner("Procesando texto..."):
                if procesar_con_gemini(PROMPT_MAESTRO + f"\nTexto: {texto_entrada}"):
                    st.rerun()

st.divider()

# --- FORMULARIO DE VERIFICACIÓN (Y BLOQUEO DE REPETIDOS) ---
st.subheader("📝 Verificación de Datos")
with st.form("registro_pedido"):
    c1, c2 = st.columns([2, 1])
    with c1:
        v_nombre = st.text_input("Nombre", value=st.session_state.temp['n'])
    with c2:
        v_telefono = st.text_input("Teléfono", value=st.session_state.temp['t'])
    
    v_direccion = st.text_input("Dirección", value=st.session_state.temp['d'])
    
    if st.form_submit_button("✅ GUARDAR EN BASE DE DATOS"):
        if v_nombre and v_telefono:
            # BLOQUEO DE CLIENTES REPETIDOS
            es_repetido = any(cliente['Tel'] == v_telefono for cliente in st.session_state.db)
            
            if es_repetido:
                st.warning(f"⚠️ El teléfono {v_telefono} ya existe en tu base de datos.")
            else:
                nuevo = {
                    "Cliente": v_nombre,
                    "Tel": v_telefono,
                    "Dir": v_direccion,
                    "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                st.session_state.db.insert(0, nuevo) # El último arriba
                st.session_state.temp = {'n': '', 't': '', 'd': ''} # Limpiar
                st.success(f"¡{v_nombre} guardado correctamente!")
                st.rerun()
        else:
            st.error("Nombre y Teléfono son obligatorios.")

# --- BASE DE DATOS, WHATSAPP Y DESCARGA ---
if st.session_state.db:
    st.divider()
    df = pd.DataFrame(st.session_state.db)
    
    col_t, col_d = st.columns([2, 1])
    with col_t:
        st.subheader("📊 Base de Datos")
    with col_d:
        # BOTÓN DESCARGAR EXCEL (CSV)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Bajar Excel", csv, "base_tropiexpress.csv", "text/csv")

    st.dataframe(df, use_container_width=True, hide_index=True)

    # MENSAJE DE BIENVENIDA WHATSAPP
    ultimo = st.session_state.db[0]
    tel_wa = ultimo['Tel']
    if len(tel_wa) >= 10:
        if not tel_wa.startswith("57"): tel_wa = "57" + tel_wa
        mensaje = f"Hola {ultimo['Cliente']}, bienvenido a TropiExpress. Recibimos tu pedido correctamente."
        link_wa = f"https://wa.me/{tel_wa}?text={mensaje.replace(' ', '%20')}"
        st.link_button(f"📲 Enviar Bienvenida a {ultimo['Cliente']}", link_wa)
