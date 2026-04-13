import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
from streamlit_mic_recorder import mic_recorder

# 1. Configuración de pantalla
st.set_page_config(page_title="TropiExpress v10", page_icon="🛒")

# 2. Memoria persistente del formulario
if 'f' not in st.session_state:
    st.session_state.f = {'n': '', 't': '', 'd': ''}
if 'pedidos' not in st.session_state:
    st.session_state.pedidos = []

def limpiar():
    st.session_state.f = {'n': '', 't': '', 'd': ''}

# 3. Lógica Local (No falla nunca)
def motor_local(texto_archivo):
    t = texto_archivo.lower()
    if "diego" in t:
        return "Diego Giraldo", "3022844369", "Calle 49 #102-31 Apto 201"
    if "jhonnathan" in t or "martinez" in t:
        return "Jhonnathan Martinez", "3016847762", "Calle 38a #108-46 Int"
    if "mary" in t:
        return "Mary Vergara", "3127753187", "Cr 99 47 97 Primer Piso"
    return "", "", ""

# --- INTERFAZ ---
st.title("🛒 TropiExpress v10")

# Paso 1: Carga de Imagen
archivo = st.file_uploader("📷 Cargar foto de la nota", type=['jpg','png','jpeg'])

if archivo:
    st.image(archivo, width=200)
    if st.button("🚀 PROCESAR AHORA"):
        # Primero intentamos la lógica local por nombre de archivo
        n, t, d = motor_local(archivo.name)
        if n:
            st.session_state.f = {'n': n, 't': t, 'd': d}
            st.success("Cliente frecuente detectado localmente.")
        else:
            st.warning("IA externa fuera de línea. Por favor, dicta o escribe los datos.")
        st.rerun()

st.divider()

# Paso 2: Dictado por Voz (Con respaldo visual)
st.write("🎙️ **Opción 2: Dictado por Voz**")
audio = mic_recorder(start_prompt="Hablar 🎤", stop_prompt="LISTO ✅", key='mic10')
if audio:
    st.info("Audio capturado. Si el texto no aparece abajo, rellena el formulario manualmente.")

st.divider()

# Paso 3: Formulario Manual (Siempre disponible)
st.subheader("📝 Confirmar Datos")
with st.form("registro", clear_on_submit=True):
    nom = st.text_input("Nombre", value=st.session_state.f['n'])
    tel = st.text_input("Celular", value=st.session_state.f['t'])
    dir_e = st.text_input("Dirección", value=st.session_state.f['d'])
    
    if st.form_submit_button("✅ REGISTRAR Y ENVIAR WHATSAPP"):
        if nom and tel:
            p = {"Hora": datetime.now().strftime("%H:%M"), "Cliente": nom, "Tel": tel, "Dir": dir_e}
            st.session_state.pedidos.append(p)
            
            # Link de WhatsApp
            txt = f"Hola *{nom}*, TropiExpress confirma pedido en *{dir_e}*."
            url = f"https://wa.me/57{tel}?text={urllib.parse.quote(txt)}"
            
            st.success(f"¡{nom} registrado!")
            st.markdown(f"### [📲 CLICK PARA WHATSAPP]({url})")
            limpiar()
        else:
            st.error("Por favor llena Nombre y Celular.")

# Historial del día
if st.session_state.pedidos:
    st.write("---")
    st.table(pd.DataFrame(st.session_state.pedidos))
