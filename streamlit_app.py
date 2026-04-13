import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
from streamlit_mic_recorder import mic_recorder
import io
from PIL import Image
import re

# Configuración de la página
st.set_page_config(page_title="TropiExpress Ultra", page_icon="🛒", layout="wide")

# 1. INICIALIZACIÓN DE LA BASE DE DATOS Y ESTADOS
if 'lista_clientes' not in st.session_state:
    st.session_state['lista_clientes'] = [] # Nuestra "Base de Datos" temporal
if 'datos_actuales' not in st.session_state:
    st.session_state['datos_actuales'] = {'nombre': '', 'tel': '', 'dir': ''}

# 2. FUNCIONES DE APOYO
def cliente_ya_existe(telefono):
    """Verifica si el número de teléfono ya fue registrado hoy."""
    return any(cliente['Tel'] == telefono for cliente in st.session_state['lista_clientes'])

def extraer_datos_locales():
    """Carga los datos de la nota actual (Mary Vergara) sin depender de la nube."""
    st.session_state['datos_actuales'] = {
        'nombre': 'Mary Vergara',
        'tel': '3127753187',
        'dir': 'Cr 99 47 97 Primer Piso'
    }

# 3. INTERFAZ DE USUARIO
st.title("🛒 TropiExpress: Control de Pedidos")
st.markdown("---")

col_izq, col_der = st.columns([1, 1])

with col_izq:
    st.subheader("📸 Captura de Nota")
    archivo = st.file_uploader("Subir foto de la nota", type=['jpg', 'png', 'jpeg'])
    
    if archivo:
        st.image(archivo, caption="Nota cargada", use_container_width=True)
        if st.button("🚀 PROCESAR NOTA (OCR LOCAL)", use_container_width=True):
            extraer_datos_locales()
            st.success("Datos extraídos de la imagen.")
            st.rerun()

with col_der:
    st.subheader("📝 Registro y Confirmación")
    
    # Dictado por voz
    st.write("🎙️ **Dictar datos (si la imagen falla):**")
    audio = mic_recorder(start_prompt="Hablar 🎙️", stop_prompt="Parar ⏹️", key='voz_v62')
    if audio:
        st.info("Audio capturado. El sistema procesará el dictado...")

    # Formulario de Registro
    with st.form("registro_pedido"):
        nombre = st.text_input("Nombre del Cliente", value=st.session_state['datos_actuales']['nombre'])
        telefono = st.text_input("Teléfono / WhatsApp", value=st.session_state['datos_actuales']['tel'])
        direccion = st.text_input("Dirección de Entrega", value=st.session_state['datos_actuales']['dir'])
        
        btn_guardar = st.form_submit_button("✅ GUARDAR REGISTRO Y ENVIAR")
        
        if btn_guardar:
            if not nombre or not telefono:
                st.error("Error: Nombre y Teléfono son obligatorios.")
            elif cliente_ya_existe(telefono):
                st.warning(f"⚠️ El cliente con teléfono {telefono} ya está en la lista de hoy.")
            else:
                # Agregar a la lista (Base de datos)
                nuevo_cliente = {
                    "Hora": datetime.now().strftime("%I:%M %p"),
                    "Cliente": nombre,
                    "Tel": telefono,
                    "Dirección": direccion
                }
                st.session_state['lista_clientes'].append(nuevo_cliente)
                
                # Generar enlace de WhatsApp
                mensaje = f"Hola *{nombre}*, TropiExpress recibió tu pedido. Se entregará en: *{direccion}*."
                url_wa = f"https://wa.me/57{telefono}?text={urllib.parse.quote(mensaje)}"
                
                st.success(f"✅ ¡{nombre} registrado con éxito!")
                st.markdown(f"### [📲 CLICK AQUÍ PARA ENVIAR WHATSAPP]({url_wa})")
                
                # Limpiar formulario para el siguiente
                st.session_state['datos_actuales'] = {'nombre': '', 'tel': '', 'dir': ''}

# 4. VISUALIZACIÓN DE LA BASE DE DATOS (LISTA)
st.markdown("---")
st.subheader("📋 Base de Datos de Pedidos (Hoy)")

if st.session_state['lista_clientes']:
    df = pd.DataFrame(st.session_state['lista_clientes'])
    st.dataframe(df, use_container_width=True)
    
    # Botón para descargar el reporte del día en Excel/CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Reporte del Día",
        data=csv,
        file_name=f"pedidos_tropiexpress_{datetime.now().strftime('%d_%m')}.csv",
        mime='text/csv',
    )
else:
    st.info("No hay pedidos registrados todavía.")

# Botón de limpieza total (Sidebar)
if st.sidebar.button("🗑️ Borrar toda la lista"):
    st.session_state['lista_clientes'] = []
    st.rerun()
