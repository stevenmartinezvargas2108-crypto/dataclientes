import streamlit as st
import google.generativeai as genai
import PIL.Image
import json
import urllib.parse
import re

# --- 1. CONFIGURACIÓN DE SEGURIDAD (API KEY) ---
try:
    API_KEY = st.secrets["GEN_API_KEY"]
except Exception:
    API_KEY = "AIzaSyD60MZOaP71Qt_LNSmbVjRI5tjazT-sIiQ" 

genai.configure(api_key=API_KEY)

# --- 2. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress AI", page_icon="🛒", layout="centered")

if 'datos' not in st.session_state:
    st.session_state['datos'] = {'nombre': '', 'tel': '', 'dir': ''}

# --- 3. LÓGICA DE INTELIGENCIA ARTIFICIAL ---
def analizar_pedido_con_gemini(imagen):
    """Envía la imagen a Gemini para extraer datos estructurados."""
    # Se utiliza 'gemini-1.5-flash-latest' para mayor compatibilidad
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    prompt = """
    Analiza esta nota de pedido. 
    Extrae con precisión:
    1. Nombre del cliente (si no existe, pon "No especificado").
    2. Teléfono de contacto (solo los 10 dígitos).
    3. Dirección de entrega completa (incluyendo notas como 'primer piso').
    
    Responde estrictamente en formato JSON válido:
    {"nombre": "...", "tel": "...", "dir": "..."}
    """
    
    try:
        # Generar contenido
        response = model.generate_content([prompt, imagen])
        
        # Limpieza robusta del JSON usando Regex
        texto_respuesta = response.text
        match = re.search(r'\{.*\}', texto_respuesta, re.DOTALL)
        
        if match:
            return json.loads(match.group())
        else:
            st.error("La IA no devolvió un formato JSON válido.")
            return None
            
    except Exception as e:
        st.error(f"Error en la IA: {e}")
        return None

# --- 4. FUNCIÓN DE VOZ ---
def sintetizar_voz(texto):
    """Usa la API de voz del navegador."""
    if texto:
        componente_voz = f"""
        <script>
        var msg = new SpeechSynthesisUtterance('{texto}');
        msg.lang = 'es-CO';
        msg.rate = 1;
        window.speechSynthesis.speak(msg);
        </script>
        """
        st.components.v1.html(componente_voz, height=0)

# --- 5. INTERFAZ DE USUARIO ---
st.title("🛒 Tropiexpress Ultra-Extract")
st.markdown("### Automatización de Pedidos con Gemini 1.5 Flash")

archivo = st.file_uploader("📷 Sube la foto del pedido", type=['jpg', 'jpeg', 'png'])

if archivo:
    img = PIL.Image.open(archivo)
    st.image(img, caption="Documento cargado", width=350)

    if st.button("🚀 EXTRAER DATOS CON IA"):
        with st.spinner("Analizando documento..."):
            resultado = analizar_pedido_con_gemini(img)
            if resultado:
                st.session_state['datos'] = {
                    'nombre': resultado.get('nombre', '').title(),
                    'tel': resultado.get('tel', ''),
                    'dir': resultado.get('dir', '').title()
                }
                st.success("¡Datos extraídos!")

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

# --- 7. ACCIONES ---
if st.button("🔊 Escuchar Resumen"):
    resumen = f"Pedido para {nombre_f}. Dirección: {dir_f}. Celular: {tel_f}."
    sintetizar_voz(resumen)

if btn_guardar:
    if tel_f:
        # Limpieza de teléfono para el link (solo números)
        tel_limpio = "".join(filter(str.isdigit, tel_f))
        
        # Si el número no tiene el prefijo de país, se asume Colombia (+57)
        whatsapp_num = f"57{tel_limpio}" if len(tel_limpio) == 10 else tel_limpio
        
        texto_wa = f"Hola {nombre_f}, bienvenido a Tropiexpress 🛒.\n\n" \
                   f"Confirmamos tu pedido. Beneficio: {promo}.\n" \
                   f"📍 Entrega: {dir_f}\n\n" \
                   f"¿Los datos son correctos?"
        
        link_wa = f"https://wa.me/{whatsapp_num}?text={urllib.parse.quote(texto_wa)}"
        
        st.markdown(f"""
            <a href="{link_wa}" target="_blank" style="text-decoration: none;">
                <div style="background-color: #25D366; color: white; padding: 15px; text-align: center; border-radius: 10px; font-weight: bold; font-size: 18px; margin-top: 10px;">
                    📲 ABRIR WHATSAPP DEL CLIENTE
                </div>
            </a>
        """, unsafe_allow_html=True)
    else:
        st.warning("Por favor, verifica el número de teléfono.")
