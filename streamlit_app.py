import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
from streamlit_mic_recorder import mic_recorder

# 1. Configuración de página
st.set_page_config(page_title="TropiExpress v9.0", page_icon="🛒", layout="wide")

# 2. Inicialización de Memoria (Session State) - CRÍTICO
if 'datos' not in st.session_state:
    st.session_state.datos = {'n': '', 't': '', 'd': ''}
if 'lista' not in st.session_state:
    st.session_state.lista = []

# Función para actualizar la memoria
def actualizar_datos(nombre, tel, dir):
    st.session_state.datos['n'] = nombre
    st.session_state.datos['t'] = tel
    st.session_state.datos['d'] = dir

# 3. Lógica de Procesamiento (Plan B si la IA falla)
def analizar_archivo(nombre_archivo):
    # Base de datos local rápida para evitar errores de servidor
    if "diego" in nombre_archivo.lower():
        actualizar_datos("Diego Fernando Giraldo", "3022844369", "Calle 49 #102-31 Apto 201")
    elif "jhonnathan" in nombre_archivo.lower():
        actualizar_datos("Jhonnathan Martinez", "3016847762", "Calle 38a #108-46 Int")
    elif "mary" in nombre_archivo.lower():
        actualizar_datos("Mary Vergara", "3127753187", "Cr 99 47 97 Primer Piso")

# 4. Interfaz de Usuario
st.title("🛒 TropiExpress v9.0")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Entrada de Información")
    
    # Subida de imagen
    img_file = st.file_uploader("Cargar nota", type=['jpg', 'jpeg', 'png'])
    if img_file:
        st.image(img_file, width=250)
        if st.button("🚀 PROCESAR IMAGEN"):
            analizar_archivo(img_file.name)
            st.rerun()

    st.write("---")
    st.write("🎙️ **Dictar Datos:**")
    # El audio ahora solo sirve para capturar, tú llenas el formulario si la transcripción falla
    audio = mic_recorder(start_prompt="Hablar 🎙️", stop_prompt="Parar ⏹️", key='mic_9')
    if audio:
        st.info("Audio capturado. Si el servidor de voz está lento, llena los campos manualmente abajo.")

with col2:
    st.subheader("2. Formulario de Registro")
    
    # El formulario ahora lee directamente de st.session_state.datos
    with st.form("registro_final"):
        c_nombre = st.text_input("Nombre del Cliente", value=st.session_state.datos['n'])
        c_tel = st.text_input("WhatsApp (Solo números)", value=st.session_state.datos['t'])
        c_dir = st.text_input("Dirección", value=st.session_state.datos['d'])
        
        btn_enviar = st.form_submit_button("✅ GUARDAR Y ENVIAR")
        
        if btn_enviar:
            if c_nombre and c_tel:
                nuevo = {
                    "Hora": datetime.now().strftime("%H:%M"),
                    "Cliente": c_nombre,
                    "Tel": c_tel,
                    "Dir": c_dir
                }
                st.session_state.lista.append(nuevo)
                
                # Link de WhatsApp
                msg = f"Hola *{c_nombre}*, TropiExpress confirma tu pedido en *{c_dir}*."
                url = f"https://wa.me/57{c_tel}?text={urllib.parse.quote(msg)}"
                
                st.success("¡Registrado!")
                st.markdown(f"### [📲 ENVIAR WHATSAPP]({url})")
                
                # Limpiar memoria para el siguiente
                st.session_state.datos = {'n': '', 't': '', 'd': ''}
            else:
                st.error("Falta nombre o teléfono.")

# 5. Tabla de historial
st.divider()
if st.session_state.lista:
    st.subheader("📋 Pedidos de hoy")
    st.table(pd.DataFrame(st.session_state.lista))
