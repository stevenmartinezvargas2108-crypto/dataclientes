import streamlit as st
import google.generativeai as genai
import PIL.Image
import json
import urllib.parse
import re
import pandas as pd
from io import BytesIO

# --- 1. CONFIGURACIÓN DE SEGURIDAD ---
# Asegúrate de poner 'GEN_API_KEY' en los Secrets de Streamlit Cloud
try:
    API_KEY = st.secrets["GEN_API_KEY"]
except Exception:
    API_KEY = "AIzaSyD60MZOaP71Qt_LNSmbVjRI5tjazT-sIiQ" 

genai.configure(api_key=API_KEY)

# --- 2. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress Ultra-Extract", page_icon="🛒", layout="wide")

# Inicialización de estados (Base de datos temporal y datos de formulario)
if 'db_clientes' not in st.session_state:
    st.session_state['db_clientes'] = []

if 'datos_actuales' not in st.session_state:
    st.session_state['datos_actuales'] = {'nombre': '', 'tel': '', 'dir': '', 'urgencia': 'Normal'}

# --- 3. LÓGICA DE INTELIGENCIA ARTIFICIAL (CORREGIDA) ---
def analizar_pedido_con_gemini(imagen):
    if not API_KEY:
        st.error("❌ API Key no configurada. Agrégala en los Secrets de Streamlit.")
        return None
        
    # Usamos 'gemini-1.5-flash' para evitar errores de versión
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = """
    Analiza esta nota de pedido. Extrae estos campos con precisión:
    1. 'nombre': Nombre del cliente (revisa bien todas las líneas).
    2. 'tel': Solo los 10 dígitos numéricos.
    3. 'dir': Dirección completa (piso, apto, barrio).
    4. 'urgencia': 'Urgente' si el cliente lo pide o 'Normal' si no.
    
    Responde ÚNICAMENTE en este formato JSON:
    {"nombre": "...", "tel": "...", "dir": "...", "urgencia": "..."}
    """
    
    try:
        response = model.generate_content([prompt, imagen])
        # Limpieza de la respuesta para extraer solo el JSON
        texto = response.text
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        
        if match:
            return json.loads(match.group())
        else:
            st.error("La IA no generó un formato válido. Intenta de nuevo.")
            return None
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- 4. COMPONENTE DE DICTADO POR VOZ (JS) ---
def componente_dictado():
    st.markdown("""
        <script>
        function startDictation() {
            const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.lang = 'es-CO';
            recognition.onresult = (event) => {
                const text = event.results[0][0].transcript;
                alert("Texto dictado: " + text + "\\n\\nPor favor, escríbelo en el campo correspondiente.");
            };
            recognition.start();
        }
        </script>
        <button onclick="startDictation()" style="background-color: #f0f2f6; border: 1px solid #dcdfe6; padding: 10px; border-radius: 8px; cursor: pointer; width: 100%; margin-bottom: 10px;">
            🎤 Iniciar Dictado por Voz (Micrófono)
        </button>
    """, unsafe_allow_html=True)

# --- 5. INTERFAZ DE USUARIO ---
st.title("🛒 Tropiexpress AI: Extractor de Pedidos")

col_foto, col_form = st.columns([1, 1.2])

with col_foto:
    st.subheader("📷 Cargar Documento")
    archivo = st.file_uploader("Sube la foto del pedido", type=['jpg', 'jpeg', 'png'])

    if archivo:
        img = PIL.Image.open(archivo)
        st.image(img, caption="Imagen cargada", use_container_width=True)

        if st.button("🚀 EXTRAER DATOS CON IA"):
            with st.spinner("Gemini analizando..."):
                resultado = analizar_pedido_con_gemini(img)
                if resultado:
                    st.session_state['datos_actuales'] = {
                        'nombre': resultado.get('nombre', '').title(),
                        'tel': resultado.get('tel', ''),
                        'dir': resultado.get('dir', '').title(),
                        'urgencia': resultado.get('urgencia', 'Normal')
                    }
                    st.success("¡Datos extraídos con éxito!")

with col_form:
    st.subheader("📝 Confirmar Pedido")
    componente_dictado()
    
    with st.form("form_registro"):
        nombre_f = st.text_input("Nombre Cliente", value=st.session_state['datos_actuales']['nombre'])
        tel_f = st.text_input("Celular (10 dígitos)", value=st.session_state['datos_actuales']['tel'])
        dir_f = st.text_input("Dirección de Entrega", value=st.session_state['datos_actuales']['dir'])
        
        c1, c2 = st.columns(2)
        with c1:
            promo = st.selectbox("Beneficio", ["Envío Gratis 🚚", "Bono $5.000 🎁", "Obsequio 🎀"])
        with c2:
            prioridad = st.selectbox("Prioridad", ["Normal", "Urgente"], 
                                    index=0 if st.session_state['datos_actuales']['urgencia'] == 'Normal' else 1)

        btn_guardar = st.form_submit_button("✅ GUARDAR Y GENERAR WHATSAPP")

    if btn_guardar:
        # Guardar en la "Base de Datos" local
        registro = {
            "Fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "Cliente": nombre_f,
            "Teléfono": tel_f,
            "Dirección": dir_f,
            "Promo": promo,
            "Prioridad": prioridad
        }
        st.session_state['db_clientes'].append(registro)
        
        # Lógica de WhatsApp
        tel_limpio = "".join(filter(str.isdigit, tel_f))
        wa_num = f"57{tel_limpio}" if len(tel_limpio) == 10 else tel_limpio
        texto_wa = f"Hola {nombre_f} 👋, Tropiexpress confirma tu pedido.\n📍 Dirección: {dir_f}\n🎁 Beneficio: {promo}\n🚀 Estado: {prioridad}"
        link_wa = f"https://wa.me/{wa_num}?text={urllib.parse.quote(texto_wa)}"
        
        st.markdown(f"""
            <a href="{link_wa}" target="_blank" style="text-decoration:none;">
                <div style="background-color:#25D366; color:white; padding:15px; text-align:center; border-radius:10px; font-weight:bold; font-size:18px;">
                    📲 ENVIAR WHATSAPP
                </div>
            </a>
        """, unsafe_allow_html=True)

# --- 6. BASE DE DATOS Y EXPORTACIÓN ---
st.divider()
st.subheader("📊 Pedidos Registrados Hoy")

if st.session_state['db_clientes']:
    df = pd.DataFrame(st.session_state['db_clientes'])
    st.table(df) # O usar st.dataframe(df) para que sea interactiva

    # Crear archivo Excel en memoria
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Pedidos_Hoy')
    
    st.download_button(
        label="📥 DESCARGAR EXCEL",
        data=output.getvalue(),
        file_name=f"tropiexpress_{pd.Timestamp.now().strftime('%d_%m_%Y')}.xlsx",
        mime="application/vnd.ms-excel"
    )
else:
    st.info("No hay pedidos guardados en esta sesión.")
