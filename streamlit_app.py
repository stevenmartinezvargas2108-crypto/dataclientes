import streamlit as st
import google.generativeai as genai
import PIL.Image
import json
import urllib.parse
import os

# --- 1. CONFIGURACIÓN DE SEGURIDAD (API KEY) ---
# Intenta obtener la clave de los Secrets de Streamlit (GitHub) o localmente
try:
    API_KEY = st.secrets["GEN_API_KEY"]
except Exception:
    # Si trabajas local, asegúrate de tenerla en una variable de entorno o búscala aquí
    API_KEY = "AIzaSyBauf8AlM9GDlyHAkRBKDvNClGzgSOrQMk" 

genai.configure(api_key=API_KEY)

# --- 2. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress AI", page_icon="🛒", layout="centered")

if 'datos' not in st.session_state:
    st.session_state['datos'] = {'nombre': '', 'tel': '', 'dir': ''}

# --- 3. LÓGICA DE INTELIGENCIA ARTIFICIAL ---
def analizar_pedido_con_gemini(imagen):
    """Envía la imagen a Gemini para extraer datos estructurados."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Prompt optimizado para evitar errores en "últimas líneas" o datos basura
    prompt = """
    Analiza esta nota de pedido de un supermercado. 
    Extrae con precisión:
    1. Nombre del cliente.
    2. Teléfono de contacto (10 dígitos que empiezan por 3).
    3. Dirección de entrega completa.
    
    Ignora cualquier texto que no sea relevante para estos tres campos.
    Responde estrictamente en formato JSON:
    {"nombre": "...", "tel": "...", "dir": "..."}
    """
    
    try:
        response = model.generate_content([prompt, imagen])
        # Limpieza por si la IA devuelve bloques de código markdown
        json_str = response.text.replace('json', '').replace('', '').strip()
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Error en la IA: {e}")
        return None

# --- 4. FUNCIÓN DE VOZ (LECTURA) ---
def sintetizar_voz(texto):
    """Usa la API de voz del navegador para leer el texto."""
    if texto:
        componente_voz = f"""
        <script>
        var msg = new SpeechSynthesisUtterance('{texto}');
        msg.lang = 'es-CO'; // Español de Colombia
        msg.rate = 1;
        window.speechSynthesis.speak(msg);
        </script>
        """
        st.components.v1.html(componente_voz, height=0)

# --- 5. INTERFAZ DE USUARIO ---
st.title("🛒 Tropiexpress Ultra-Extract")
st.markdown("### Automatización de Pedidos con IA de Google")

archivo = st.file_uploader("📷 Sube la foto del pedido", type=['jpg', 'jpeg', 'png'])

if archivo:
    img = PIL.Image.open(archivo)
    st.image(img, caption="Documento cargado", width=350)

    if st.button("🚀 EXTRAER DATOS CON IA"):
        with st.spinner("Gemini analizando el pedido..."):
            resultado = analizar_pedido_con_gemini(img)
            if resultado:
                st.session_state['datos'] = {
                    'nombre': resultado.get('nombre', '').title(),
                    'tel': resultado.get('tel', ''),
                    'dir': resultado.get('dir', '').title()
                }
                st.success("¡Datos extraídos con éxito!")

st.divider()

# --- 6. FORMULARIO DE REVISIÓN ---
with st.form("confirmacion_datos"):
    st.subheader("📝 Confirmación de Datos")
    col1, col2 = st.columns(2)
    
    with col1:
        nombre_f = st.text_input("Nombre Cliente", value=st.session_state['datos']['nombre'])
        tel_f = st.text_input("Celular (10 dígitos)", value=st.session_state['datos']['tel'])
    
    with col2:
        dir_f = st.text_input("Dirección", value=st.session_state['datos']['dir'])
        promo = st.selectbox("Estrategia", ["Envío Gratis 🚚", "Bono $5.000 🎁", "Obsequio Sorpresa 🎀"])

    btn_guardar = st.form_submit_button("✅ Guardar y Generar Enlace")

# --- 7. BOTÓN DE VOZ Y ACCIONES ---
col_voz, col_wa = st.columns(2)

with col_voz:
    if st.button("🔊 Escuchar Resumen"):
        resumen = f"Pedido para {nombre_f}. Dirección: {dir_f}. Celular: {tel_f}."
        sintetizar_voz(resumen)

if btn_guardar:
    if nombre_f and tel_f:
        # Limpieza de teléfono para el link
        tel_limpio = "".join(filter(str.isdigit, tel_f))
        
        texto_wa = f"Hola {nombre_f}, bienvenido a Tropiexpress 🛒.\n\n" \
                   f"Confirmamos tu pedido. Beneficio aplicado: {promo}.\n" \
                   f"📍 Entrega: {dir_f}\n\n" \
                   f"¿Los datos son correctos?"
        
        link_wa = f"https://wa.me/57{tel_limpio}?text={urllib.parse.quote(texto_wa)}"
        
        st.markdown(f"""
            <a href="{link_wa}" target="_blank" style="text-decoration: none;">
                <div style="background-color: #25D366; color: white; padding: 15px; text-align: center; border-radius: 10px; font-weight: bold; font-size: 18px; margin-top: 10px;">
                    📲 ABRIR WHATSAPP DEL CLIENTE
                </div>
            </a>
        """, unsafe_allow_html=True)
    else:
        st.warning("Asegúrate de que el nombre y el teléfono estén presentes.")
