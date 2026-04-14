import streamlit as st
import pandas as pd
from datetime import datetime
import json
import re
from PIL import Image
import google.generativeai as genai

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TropiExpress IA v22", page_icon="🛒", layout="centered")

# Estilos para facilitar el uso en celular
st.markdown("""
<style>
    .main { background-color: #f5f7f9; }
    .stButton button { width: 100%; height: 3.5rem; font-weight: bold; font-size: 1.1rem; border-radius: 10px; }
    div[data-testid="stForm"] { border: 2px solid #ff4b4b; border-radius: 15px; background-color: white; padding: 20px; }
    .stTextInput input { font-size: 1.2rem !important; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE ESTADOS ---
if 'temp' not in st.session_state:
    st.session_state.temp = {'n': '', 't': '', 'd': ''}
if 'db' not in st.session_state:
    st.session_state.db = []

# --- FUNCIÓN MAESTRA IA (CORREGIDA) ---
def procesar_con_gemini(prompt_text, imagen_pil=None):
    try:
        # 1. Configuración con tu Secret
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("Falta la GEMINI_API_KEY en los Secrets de Streamlit.")
            return False
            
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        
        # 2. Selección del modelo (Nombre oficial para evitar Error 404)
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        # 3. Preparar contenido
        if imagen_pil:
            contenido = [prompt_text, imagen_pil]
        else:
            contenido = [prompt_text]
            
        # 4. Generación
        response = model.generate_content(contenido)
        
        # 5. Limpieza de la respuesta para obtener JSON puro
        raw_text = response.text
        # Quitamos bloques de código si la IA los pone
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        
        if json_match:
            datos = json.loads(json_match.group())
            st.session_state.temp['n'] = str(datos.get('nombre', '')).title().strip()
            st.session_state.temp['t'] = re.sub(r'\D', '', str(datos.get('telefono', ''))).strip()
            st.session_state.temp['d'] = str(datos.get('direccion', '')).upper().strip()
            return True
        else:
            st.error("La IA no pudo formatear los datos correctamente. Intenta de nuevo.")
            return False
            
    except Exception as e:
        st.error(f"Error técnico: {e}")
        return False

# --- INTERFAZ DE USUARIO ---
st.title("🛒 TropiExpress IA Vision")
st.info("Captura pedidos de fotos o dictados y organiza tu base de datos.")

tab_foto, tab_voz = st.tabs(["📸 Foto de Nota", "🎙️ Dictado / Texto"])

# Prompt para instruir a la IA
INSTRUCCIONES = """
Analiza la información proporcionada y extrae los datos del cliente.
Responde estrictamente en formato JSON:
{"nombre": "...", "telefono": "...", "direccion": "..."}
Si un dato no existe, deja "". No inventes información.
"""

with tab_foto:
    archivo = st.file_uploader("Sube la foto del pedido", type=['jpg','jpeg','png'])
    if archivo:
        img_display = Image.open(archivo)
        st.image(img_display, caption="Vista previa", use_column_width=True)
        if st.button("EXTRAER DATOS DE FOTO 🚀"):
            with st.spinner("Gemini analizando imagen..."):
                if procesar_con_gemini(INSTRUCCIONES, img_display):
                    st.success("¡Datos extraídos!")
                    st.rerun()

with tab_voz:
    texto_libre = st.text_area("Pega el pedido o usa el dictado de voz:", height=150)
    if st.button("PROCESAR TEXTO 🚀"):
        if texto_libre:
            with st.spinner("Procesando datos..."):
                if procesar_con_gemini(INSTRUCCIONES + f"\nTexto: {texto_libre}"):
                    st.success("¡Datos listos!")
                    st.rerun()

st.divider()

# --- FORMULARIO DE VERIFICACIÓN ---
st.subheader("📝 Verificación y Registro")
with st.form("registro_final"):
    col1, col2 = st.columns([2, 1])
    with col1:
        nombre_final = st.text_input("Nombre Cliente", value=st.session_state.temp['n'])
    with col2:
        tel_final = st.text_input("Teléfono", value=st.session_state.temp['t'])
    
    dir_final = st.text_input("Dirección", value=st.session_state.temp['d'])
    
    confirmar = st.form_submit_button("✅ GUARDAR CLIENTE")
    
    if confirmar:
        if nombre_final and tel_final:
            # Control de duplicados por teléfono
            es_duplicado = any(c['Tel'] == tel_final for c in st.session_state.db)
            if es_duplicado:
                st.warning(f"El teléfono {tel_final} ya existe en la base de datos.")
            else:
                nuevo_registro = {
                    "Cliente": nombre_final,
                    "Tel": tel_final,
                    "Dir": dir_final,
                    "Registro": datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                st.session_state.db.insert(0, nuevo_registro)
                # Limpiar campos después de guardar
                st.session_state.temp = {'n': '', 't': '', 'd': ''}
                st.success("Cliente guardado con éxito.")
                st.rerun()
        else:
            st.error("Por favor completa Nombre y Teléfono.")

# --- BASE DE DATOS Y WHATSAPP ---
if st.session_state.db:
    st.divider()
    st.subheader("📊 Clientes Registrados")
    df = pd.DataFrame(st.session_state.db)
    
    # Botón de Descarga Excel
    csv_data = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Descargar Base de Datos (CSV)", csv_data, "pedidos_tropiexpress.csv", "text/csv")
    
    st.dataframe(df, use_container_width=True, hide_index=True)

    # WhatsApp para el último guardado
    ultimo = st.session_state.db[0]
    num_wa = ultimo['Tel']
    if len(num_wa) >= 7:
        # Ajuste para Colombia (57)
        if not num_wa.startswith("57"): num_wa = "57" + num_wa
        texto_wa = f"Hola {ultimo['Cliente']}, bienvenido a TropiExpress. Hemos recibido tu información correctamente."
        url_wa = f"https://wa.me/{num_wa}?text={texto_wa.replace(' ', '%20')}"
        st.link_button(f"📲 Enviar WhatsApp a {ultimo['Cliente']}", url_wa)
