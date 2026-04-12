import streamlit as st
import google.generativeai as genai
import PIL.Image
import json
import urllib.parse
import re
import pandas as pd
from io import BytesIO

# --- 1. CONFIGURACIÓN DE SEGURIDAD (API KEY) ---
# En GitHub/Streamlit Cloud, configura esto en 'Secrets'
try:
    API_KEY = st.secrets["GEN_API_KEY"]
except Exception:
    API_KEY = "AIzaSyD60MZOaP71Qt_LNSmbVjRI5tjazT-sIiQ" # Deja vacío para que el usuario pueda ingresarla si falla

genai.configure(api_key=API_KEY)

# --- 2. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress Ultra-Extract", page_icon="🛒", layout="wide")

# Inicialización del historial de clientes (Base de datos temporal)
if 'db_clientes' not in st.session_state:
    st.session_state['db_clientes'] = []

if 'datos_actuales' not in st.session_state:
    st.session_state['datos_actuales'] = {'nombre': '', 'tel': '', 'dir': '', 'urgencia': 'Normal'}

# --- 3. LÓGICA DE INTELIGENCIA ARTIFICIAL ---
def analizar_pedido_con_gemini(imagen):
    if not API_KEY:
        st.error("❌ API Key no configurada. Revisa los Secrets de Streamlit.")
        return None
        
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    prompt = """
    Analiza esta nota de pedido de Tropiexpress. 
    Extrae con precisión:
    1. 'nombre': Nombre del cliente.
    2. 'tel': Solo los 10 dígitos.
    3. 'dir': Dirección completa.
    4. 'urgencia': Clasifica como 'Urgente' si hay notas de rapidez o 'Normal' si no.
    
    Responde estrictamente en formato JSON válido:
    {"nombre": "...", "tel": "...", "dir": "...", "urgencia": "..."}
    """
    
    try:
        response = model.generate_content([prompt, imagen])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None
    except Exception as e:
        st.error(f"Error en la IA: {e}")
        return None

# --- 4. COMPONENTE DE DICTADO POR VOZ (JavaScript) ---
def componente_dictado():
    st.markdown("""
        <script>
        function startDictation() {
            const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.lang = 'es-CO';
            recognition.onresult = (event) => {
                const text = event.results[0][0].transcript;
                const input = window.parent.document.querySelectorAll('input[aria-label="Nombre Cliente"]')[0];
                alert("Escuché: " + text + ". Por favor, escríbelo o confírmalo en el campo.");
            };
            recognition.start();
        }
        </script>
        <button onclick="startDictation()" style="background-color: #f0f2f6; border: 1px solid #dcdfe6; padding: 10px; border-radius: 5px; cursor: pointer;">
            🎤 Iniciar Dictado por Voz
        </button>
    """, unsafe_allow_html=True)

# --- 5. INTERFAZ DE USUARIO ---
st.title("🛒 Tropiexpress AI: Gestión de Pedidos")

col_izq, col_der = st.columns([1, 1])

with col_izq:
    st.subheader("📸 Captura de Nota")
    archivo = st.file_uploader("Sube la foto del pedido", type=['jpg', 'jpeg', 'png'])

    if archivo:
        img = PIL.Image.open(archivo)
        st.image(img, caption="Imagen del pedido", use_container_width=True)

        if st.button("🚀 PROCESAR CON IA"):
            with st.spinner("Leyendo información..."):
                resultado = analizar_pedido_con_gemini(img)
                if resultado:
                    st.session_state['datos_actuales'] = {
                        'nombre': resultado.get('nombre', '').title(),
                        'tel': resultado.get('tel', ''),
                        'dir': resultado.get('dir', '').title(),
                        'urgencia': resultado.get('urgencia', 'Normal')
                    }
                    st.success("¡Información extraída!")

with col_der:
    st.subheader("📝 Revisión y Edición")
    
    # Botón de dictado
    componente_dictado()
    
    with st.form("formulario_edicion"):
        nombre_f = st.text_input("Nombre Cliente", value=st.session_state['datos_actuales']['nombre'])
        tel_f = st.text_input("Celular", value=st.session_state['datos_actuales']['tel'])
        dir_f = st.text_input("Dirección", value=st.session_state['datos_actuales']['dir'])
        promo = st.selectbox("Estrategia", ["Envío Gratis 🚚", "Bono $5.000 🎁", "Obsequio Sorpresa 🎀"])
        urgencia_f = st.selectbox("Prioridad", ["Normal", "Urgente"], 
                                 index=0 if st.session_state['datos_actuales']['urgencia'] == 'Normal' else 1)

        btn_guardar = st.form_submit_button("✅ Guardar en Base de Datos")

    if btn_guardar:
        nuevo_cliente = {
            "Fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "Cliente": nombre_f,
            "Teléfono": tel_f,
            "Dirección": dir_f,
            "Estrategia": promo,
            "Prioridad": urgencia_f
        }
        st.session_state['db_clientes'].append(nuevo_cliente)
        st.balloons()
        
        # Generar Link de WhatsApp
        tel_limpio = "".join(filter(str.isdigit, tel_f))
        wa_num = f"57{tel_limpio}" if len(tel_limpio) == 10 else tel_limpio
        texto_wa = f"Hola {nombre_f}, Tropiexpress confirma tu pedido.\n📍 Entrega: {dir_f}\n🎁 Beneficio: {promo}"
        link_wa = f"https://wa.me/{wa_num}?text={urllib.parse.quote(texto_wa)}"
        
        st.markdown(f'<a href="{link_wa}" target="_blank"><div style="background-color:#25D366;color:white;padding:10px;text-align:center;border-radius:5px;font-weight:bold;">📲 CONTACTAR POR WHATSAPP</div></a>', unsafe_allow_html=True)

# --- 6. BASE DE DATOS Y EXPORTACIÓN ---
st.divider()
st.subheader("📊 Base de Datos de Hoy")

if st.session_state['db_clientes']:
    df = pd.DataFrame(st.session_state['db_clientes'])
    st.dataframe(df, use_container_width=True)

    # Exportar a Excel
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Pedidos')
    
    st.download_button(
        label="📥 Descargar Base de Datos en Excel",
        data=buffer.getvalue(),
        file_name=f"pedidos_tropiexpress_{pd.Timestamp.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.ms-excel"
    )
else:
    st.info("Aún no hay clientes guardados en esta sesión.")
