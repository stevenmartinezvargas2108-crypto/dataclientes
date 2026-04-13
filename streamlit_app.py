import streamlit as st
import google.generativeai as genai
import urllib.parse
import pandas as pd
from datetime import datetime
from streamlit_mic_recorder import mic_recorder
import io
from PIL import Image

# --- CONFIGURACIÓN DE MOTORES ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Tropiexpress Ultra", page_icon="🛒")

if 'datos' not in st.session_state:
    st.session_state['datos'] = {'nombre': '', 'tel': '', 'dir': ''}
if 'lista' not in st.session_state:
    st.session_state['lista'] = []

# --- FUNCIÓN DE LECTURA (MOTOR GEMINI - MÁS ESTABLE) ---
def leer_nota_con_gemini(imagen_pil):
    prompt = "Extrae de esta nota de supermercado: Nombre del cliente, Teléfono y Dirección. Responde solo en formato JSON."
    try:
        response = model.generate_content([prompt, imagen_pil])
        # Limpieza simple de la respuesta
        texto = response.text.replace("```json", "").replace("```", "").strip()
        import json
        return json.loads(texto)
    except Exception as e:
        st.error(f"Error de IA: {e}")
        return None

st.title("🛒 Tropiexpress v5.5")

# Botón de pánico/limpieza
if st.sidebar.button("🗑️ Limpiar App"):
    st.session_state['datos'] = {'nombre': '', 'tel': '', 'dir': ''}
    st.rerun()

archivo = st.file_uploader("📸 Sube la nota de venta", type=['jpg', 'png', 'jpeg'])

col1, col2 = st.columns([1, 1])

with col1:
    if archivo:
        img = Image.open(archivo)
        st.image(img, caption="Nota detectada", use_container_width=True)
        
        if st.button("🚀 PROCESAR AHORA", use_container_width=True):
            with st.spinner("Leyendo con Gemini..."):
                res = leer_nota_con_gemini(img)
                if res:
                    st.session_state['datos'] = {
                        'nombre': res.get('nombre', res.get('Nombre', '')),
                        'tel': res.get('tel', res.get('Teléfono', '')),
                        'dir': res.get('dir', res.get('Dirección', ''))
                    }
                    st.success("¡Datos extraídos!")
                    st.rerun()

with col2:
    st.subheader("📝 Confirmación")
    
    # Dictado por voz independiente
    st.write("🎙️ **Corregir por voz:**")
    audio = mic_recorder(start_prompt="Dictar 🎙️", stop_prompt="Parar ⏹️", key='voz_v55')
    
    if audio:
        st.info("Audio capturado. (Edita los campos abajo si es necesario)")

    with st.form("registro_cliente"):
        n = st.text_input("Cliente", value=st.session_state['datos']['nombre'])
        t = st.text_input("WhatsApp", value=st.session_state['datos']['tel'])
        d = st.text_input("Dirección", value=st.session_state['datos']['dir'])
        
        enviar = st.form_submit_button("✅ GUARDAR Y ENVIAR")
        
        if enviar:
            if n and t:
                st.session_state['lista'].append({"Fecha": datetime.now().strftime("%H:%M"), "Cliente": n, "Tel": t, "Dir": d})
                # Link de WhatsApp para Medellín
                msg = f"Hola *{n}*, Tropiexpress ya tiene tu pedido. Va para: *{d}*."
                url = f"https://wa.me/57{t}?text={urllib.parse.quote(msg)}"
                st.markdown(f"### [📲 ENVIAR WHATSAPP]({url})")
            else:
                st.warning("Falta nombre o teléfono.")

if st.session_state['lista']:
    st.divider()
    st.write("### Historial de hoy")
    st.dataframe(pd.DataFrame(st.session_state['lista']), use_container_width=True)
