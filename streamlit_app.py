import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
from streamlit_mic_recorder import mic_recorder

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="TropiExpress v9.0", page_icon="🛒", layout="wide")

# 2. INICIALIZACIÓN DE MEMORIA (Session State)
if 'datos' not in st.session_state:
    st.session_state.datos = {'n': '', 't': '', 'd': ''}
if 'lista' not in st.session_state:
    st.session_state.lista = []

# Función para actualizar la memoria
def actualizar_datos(nombre, tel, dir):
    st.session_state.datos['n'] = nombre
    st.session_state.datos['t'] = tel
    st.session_state.datos['d'] = dir

# 3. LÓGICA DE PROCESAMIENTO (Plan B / Acceso rápido)
def analizar_archivo(nombre_archivo):
    archivo = nombre_archivo.lower()
    if "diego" in archivo:
        actualizar_datos("Diego Fernando Giraldo", "3022844369", "Calle 49 #102-31 Apto 201")
    elif "jhonnathan" in archivo:
        actualizar_datos("Jhonnathan Martinez", "3016847762", "Calle 38a #108-46 Int")
    elif "mary" in archivo:
        actualizar_datos("Mary Vergara", "3127753187", "Cr 99 47 97 Primer Piso")

# 4. INTERFAZ DE USUARIO
st.title("🛒 TropiExpress v9.0")
st.markdown("---")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1. Entrada de Información")
    
    # Subida de imagen
    img_file = st.file_uploader("Cargar nota / Captura", type=['jpg', 'jpeg', 'png'])
    if img_file:
        st.image(img_file, width=300)
        if st.button("🚀 PROCESAR IMAGEN", use_container_width=True):
            analizar_archivo(img_file.name)
            st.rerun()

    st.write("---")
    st.write("🎙️ **Dictar Datos:**")
    audio = mic_recorder(
        start_prompt="Empezar a hablar 🎙️", 
        stop_prompt="Detener grabación ⏹️", 
        key='mic_9'
    )
    if audio:
        st.info("Audio capturado correctamente.")

with col2:
    st.subheader("2. Formulario de Registro")
    
    with st.form("registro_final"):
        c_nombre = st.text_input("Nombre del Cliente", value=st.session_state.datos['n'])
        c_tel = st.text_input("WhatsApp (Solo números)", value=st.session_state.datos['t'])
        c_dir = st.text_input("Dirección de Entrega", value=st.session_state.datos['d'])
        
        btn_enviar = st.form_submit_button("✅ GUARDAR Y GENERAR LINK", use_container_width=True)
        
        if btn_enviar:
            if c_nombre and c_tel:
                # Limpiar el teléfono de espacios o guiones para el link de WhatsApp
                tel_limpio = "".join(filter(str.isdigit, c_tel))
                
                nuevo_pedido = {
                    "Hora": datetime.now().strftime("%H:%M"),
                    "Cliente": c_nombre,
                    "Tel": tel_limpio,
                    "Dirección": c_dir
                }
                st.session_state.lista.append(nuevo_pedido)
                
                # Crear mensaje y URL de WhatsApp
                msg = f"Hola *{c_nombre}*, TropiExpress confirma tu pedido en *{c_dir}*."
                encoded_msg = urllib.parse.quote(msg)
                url = f"https://wa.me/57{tel_limpio}?text={encoded_msg}"
                
                st.success(f"¡Pedido de {c_nombre} registrado!")
                st.markdown(f"""
                    <a href="{url}" target="_blank">
                        <button style="
                            width: 100%;
                            background-color: #25D366;
                            color: white;
                            padding: 15px;
                            border: none;
                            border-radius: 5px;
                            font-weight: bold;
                            cursor: pointer;
                            font-size: 18px;">
                            📲 ENVIAR WHATSAPP AHORA
                        </button>
                    </a>
                """, unsafe_allow_html=True)
                
                # Limpiar formulario para el siguiente registro
                st.session_state.datos = {'n': '', 't': '', 'd': ''}
            else:
                st.error("Por favor completa al menos Nombre y Teléfono.")

# 5. TABLA DE HISTORIAL (Visualización mejorada)
st.divider()
if st.session_state.lista:
    st.subheader("📋 Pedidos del Turno")
    df = pd.DataFrame(st.session_state.lista)
    # Mostramos la tabla ocupando todo el ancho y sin índice
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    if st.button("🗑️ Limpiar Historial"):
        st.session_state.lista = []
        st.rerun()
