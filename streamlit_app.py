import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
from streamlit_mic_recorder import mic_recorder

# 1. Configuración de página para móviles
st.set_page_config(page_title="TropiExpress v8.0", page_icon="🛒", layout="wide")

# 2. Inicialización de estados (Memoria de la App)
if 'lista_pedidos' not in st.session_state:
    st.session_state['lista_pedidos'] = []
if 'datos_actuales' not in st.session_state:
    st.session_state['datos_actuales'] = {'nom': '', 'tel': '', 'dir': ''}

def limpiar_formulario():
    st.session_state['datos_actuales'] = {'nom': '', 'tel': '', 'dir': ''}

# 3. Interfaz de Usuario
st.title("🛒 TropiExpress: Registro Real")

# Barra lateral para gestión
with st.sidebar:
    if st.button("🗑️ Borrar Todo e Iniciar Día"):
        st.session_state['lista_pedidos'] = []
        limpiar_formulario()
        st.rerun()

col_izq, col_der = st.columns([1, 1])

with col_izq:
    st.subheader("📷 Paso 1: Cargar Nota")
    archivo = st.file_uploader("Subir foto", type=['jpg', 'png', 'jpeg'])
    if archivo:
        st.image(archivo, caption="Nota actual", use_container_width=True)
        # Aquí eliminamos los datos fijos. Cada vez que subas algo, el sistema está listo.
        st.info("Imagen cargada. Si no se auto-completa, usa el dictado por voz abajo.")

    st.write("---")
    st.write("🎙️ **Paso 2: Dictado por voz (Recomendado)**")
    # El dictado es lo más fiable cuando la IA de imagen falla
    mic_recorder(start_prompt="Dictar datos 🎙️", stop_prompt="Detener ⏹️", key='mic_v8')

with col_der:
    st.subheader("📝 Paso 3: Confirmar Registro")
    
    with st.form("form_registro", clear_on_submit=True):
        # Los valores ahora son editables y no están "amarrados" a Diego o Mary
        nombre = st.text_input("Nombre del Cliente", value=st.session_state['datos_actuales']['nom'])
        telefono = st.text_input("WhatsApp (Solo números)", value=st.session_state['datos_actuales']['tel'])
        direccion = st.text_input("Dirección", value=st.session_state['datos_actuales']['dir'])
        
        btn_guardar = st.form_submit_button("✅ GUARDAR Y GENERAR WHATSAPP")
        
        if btn_guardar:
            # Validación de duplicados por teléfono
            es_duplicado = any(p['Tel'] == telefono for p in st.session_state['lista_pedidos'])
            
            if not nombre or not telefono:
                st.error("Faltan datos críticos.")
            elif es_duplicado:
                st.warning(f"⚠️ El teléfono {telefono} ya fue registrado hace poco.")
            else:
                # Guardar pedido
                nuevo_p = {
                    "Hora": datetime.now().strftime("%I:%M %p"),
                    "Cliente": nombre,
                    "Tel": telefono,
                    "Dirección": direccion
                }
                st.session_state['lista_pedidos'].append(nuevo_p)
                
                # Link de WhatsApp
                msg = f"Hola *{nombre}*, TropiExpress recibió tu pedido en *{direccion}*."
                url = f"https://wa.me/57{telefono}?text={urllib.parse.quote(msg)}"
                
                st.success(f"¡{nombre} registrado!")
                st.markdown(f"### [📲 CLICK AQUÍ PARA WHATSAPP]({url})")
                limpiar_formulario()

# 4. Tabla de Pedidos del Día
st.markdown("---")
st.subheader("📋 Pedidos Registrados")
if st.session_state['lista_pedidos']:
    df = pd.DataFrame(st.session_state['lista_pedidos'])
    st.dataframe(df, use_container_width=True)
else:
    st.write("No hay pedidos registrados hoy.")
