import streamlit as st
import google.generativeai as genai
import PIL.Image
import json
import urllib.parse
import re
import pandas as pd
from io import BytesIO

# --- 1. CONFIGURACIÓN DE SEGURIDAD ---
try:
    API_KEY = st.secrets["GEN_API_KEY"]
except Exception:
    API_KEY = "AIzaSyD60MZOaP71Qt_LNSmbVjRI5tjazT-sIiQ" # Si falla, se puede configurar manual en local

genai.configure(api_key=API_KEY)

# --- 2. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress Ultra-Extract", page_icon="🛒", layout="wide")

if 'db_clientes' not in st.session_state:
    st.session_state['db_clientes'] = []

if 'datos_actuales' not in st.session_state:
    st.session_state['datos_actuales'] = {'nombre': '', 'tel': '', 'dir': '', 'urgencia': 'Normal'}

# --- 3. LÓGICA DE INTELIGENCIA ARTIFICIAL ---
def analizar_pedido_con_gemini(imagen):
    if not API_KEY:
        st.error("❌ No se encontró la API Key en los Secrets de Streamlit.")
        return None
        
    try:
        # Usamos la ruta completa del modelo para evitar el error 404
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        prompt = """
        Extrae de esta nota de pedido:
        1. 'nombre': Nombre del cliente.
        2. 'tel': Los 10 dígitos del celular.
        3. 'dir': Dirección completa.
        4. 'urgencia': 'Urgente' o 'Normal'.
        
        Responde estrictamente en formato JSON.
        """
        
        # Forzamos a la IA a que entregue solo JSON
        response = model.generate_content(
            [prompt, imagen],
            generation_config={"response_mime_type": "application/json"}
        )
        
        return json.loads(response.text)
            
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        # Ayuda para diagnosticar si el modelo cambió de nombre en tu región
        if "404" in str(e):
            st.info("Intentando listar modelos disponibles para tu API Key...")
            try:
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                st.write("Modelos disponibles:", available_models)
            except:
                pass
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
                alert("Dictado capturado: " + text);
            };
            recognition.start();
        }
        </script>
        <button onclick="startDictation()" style="background-color: #f0f2f6; border: 1px solid #dcdfe6; padding: 10px; border-radius: 8px; cursor: pointer; width: 100%; margin-bottom: 15px;">
            🎤 Activar Dictado por Voz
        </button>
    """, unsafe_allow_html=True)

# --- 5. INTERFAZ DE USUARIO ---
st.title("🛒 Tropiexpress AI: Extractor de Pedidos")

col_foto, col_form = st.columns([1, 1.2])

with col_foto:
    st.subheader("📷 Cargar Nota")
    archivo = st.file_uploader("Sube la foto del pedido", type=['jpg', 'jpeg', 'png'])

    if archivo:
        img = PIL.Image.open(archivo)
        st.image(img, caption="Vista previa", use_container_width=True)

        if st.button("🚀 PROCESAR CON GEMINI FLASH"):
            with st.spinner("Analizando imagen..."):
                resultado = analizar_pedido_con_gemini(img)
                if resultado:
                    st.session_state['datos_actuales'] = {
                        'nombre': str(resultado.get('nombre', '')).title(),
                        'tel': str(resultado.get('tel', '')),
                        'dir': str(resultado.get('dir', '')).title(),
                        'urgencia': resultado.get('urgencia', 'Normal')
                    }
                    st.success("¡Datos extraídos!")

with col_form:
    st.subheader("📝 Validación de Datos")
    componente_dictado()
    
    with st.form("form_pedidos"):
        nombre_f = st.text_input("Nombre", value=st.session_state['datos_actuales']['nombre'])
        tel_f = st.text_input("Celular", value=st.session_state['datos_actuales']['tel'])
        dir_f = st.text_input("Dirección", value=st.session_state['datos_actuales']['dir'])
        
        c1, c2 = st.columns(2)
        with c1:
            promo = st.selectbox("Estrategia", ["Envío Gratis 🚚", "Bono $5.000 🎁", "Obsequio 🎀"])
        with c2:
            prioridad = st.selectbox("Prioridad", ["Normal", "Urgente"], 
                                    index=0 if st.session_state['datos_actuales']['urgencia'] == 'Normal' else 1)

        btn_guardar = st.form_submit_button("✅ GUARDAR Y PREPARAR WHATSAPP")

    if btn_guardar:
        # Guardar en historial
        st.session_state['db_clientes'].append({
            "Fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "Cliente": nombre_f,
            "Teléfono": tel_f,
            "Dirección": dir_f,
            "Estrategia": promo,
            "Prioridad": prioridad
        })
        
        # Link de WhatsApp
        tel_limpio = "".join(filter(str.isdigit, tel_f))
        wa_num = f"57{tel_limpio}" if len(tel_limpio) == 10 else tel_limpio
        texto_wa = f"Hola {nombre_f} 🛒, Tropiexpress confirma tu pedido.\n📍 Dirección: {dir_f}\n🎁 Beneficio: {promo}"
        link_wa = f"https://wa.me/{wa_num}?text={urllib.parse.quote(texto_wa)}"
        
        st.markdown(f"""
            <a href="{link_wa}" target="_blank" style="text-decoration:none;">
                <div style="background-color:#25D366; color:white; padding:15px; text-align:center; border-radius:10px; font-weight:bold;">
                    📲 ABRIR WHATSAPP
                </div>
            </a>
        """, unsafe_allow_html=True)

# --- 6. BASE DE DATOS Y EXCEL ---
st.divider()
st.subheader("📊 Historial de Pedidos")

if st.session_state['db_clientes']:
    df = pd.DataFrame(st.session_state['db_clientes'])
    st.dataframe(df, use_container_width=True)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Pedidos')
    
    st.download_button(
        label="📥 DESCARGAR BASE DE DATOS (EXCEL)",
        data=output.getvalue(),
        file_name=f"pedidos_tropiexpress_{pd.Timestamp.now().strftime('%d_%m_%Y')}.xlsx",
        mime="application/vnd.ms-excel"
    )
