import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime

# CONFIGURACIÓN BÁSICA
st.set_page_config(page_title="TropiExpress v11", page_icon="🛒")

# MEMORIA LOCAL
if 'f' not in st.session_state:
    st.session_state.f = {'n': '', 't': '', 'd': ''}
if 'lista' not in st.session_state:
    st.session_state.lista = []

# FUNCIÓN DE AUTO-RELLENADO (Basado en tus clientes frecuentes)
def auto_relleno(texto):
    t = texto.lower()
    if "diego" in t:
        st.session_state.f = {'n': 'Diego Giraldo', 't': '3022844369', 'd': 'Calle 49 #102-31 Apto 201'}
    elif "mary" in t or "vergara" in t:
        st.session_state.f = {'n': 'Mary Vergara', 't': '3127753187', 'd': 'Cr 99 47 97 Primer Piso'}
    elif "jhonnathan" in t:
        st.session_state.f = {'n': 'Jhonnathan Martinez', 't': '3016847762', 'd': 'Calle 38a #108-46 Int'}

# INTERFAZ LIMPIA
st.title("🛒 TropiExpress v11")

# 1. ENTRADA DE DATOS (REMPLAZA AL DICTADO QUE FALLA)
st.subheader("1. Entrada Rápida")
input_voz = st.text_area("Pega texto aquí o usa el Micrófono del Teclado 🎙️", 
                         placeholder="Ej: Diego Giraldo 3022844369...")

if st.button("⚡ PROCESAR TEXTO/NOMBRE"):
    auto_relleno(input_voz)
    st.rerun()

st.divider()

# 2. FORMULARIO MANUAL (SIEMPRE VISIBLE)
st.subheader("2. Confirmar y Enviar")
with st.form("form_final"):
    nom = st.text_input("Nombre", value=st.session_state.f['n'])
    tel = st.text_input("WhatsApp (Sin 57)", value=st.session_state.f['t'])
    dir = st.text_input("Dirección", value=st.session_state.f['d'])
    
    enviar = st.form_submit_button("✅ GUARDAR Y GENERAR WHATSAPP")
    
    if enviar:
        if nom and tel:
            # Guardar en historial
            pedido = {"Hora": datetime.now().strftime("%H:%M"), "Cliente": nom, "Tel": tel}
            st.session_state.lista.append(pedido)
            
            # Crear enlace
            mensaje = f"Hola *{nom}*, TropiExpress confirma pedido en *{dir}*."
            link = f"https://wa.me/57{tel}?text={urllib.parse.quote(mensaje)}"
            
            st.success("¡Registrado!")
            st.markdown(f"### [📲 ABRIR WHATSAPP AQUÍ]({link})")
            # Limpiar para el siguiente
            st.session_state.f = {'n': '', 't': '', 'd': ''}
        else:
            st.error("Faltan datos críticos.")

# HISTORIAL
if st.session_state.lista:
    st.write("---")
    st.table(pd.DataFrame(st.session_state.lista))
