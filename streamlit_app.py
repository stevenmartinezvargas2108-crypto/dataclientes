import streamlit as st
import pandas as pd
import easyocr
import numpy as np
from PIL import Image
from datetime import datetime
import re
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TropiExpress v11.0", page_icon="🛒", layout="wide")

# Inicializar EasyOCR (Carga local sin API Keys)
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es']) 

reader = load_ocr()

# Inicializar estados de memoria
if 'lista_pedidos' not in st.session_state:
    st.session_state.lista_pedidos = []
if 'datos_form' not in st.session_state:
    st.session_state.datos_form = {'n': '', 't': '', 'd': ''}

# --- FUNCIONES DE LÓGICA ---
def extraer_datos_ocr(imagen):
    img_array = np.array(imagen)
    # Leer texto de la imagen
    resultados = reader.readtext(img_array, detail=0)
    texto_sucio = " ".join(resultados)
    
    # 1. Buscar Teléfono (Patrón de 10 números seguidos)
    telefonos = re.findall(r'\d{10}', texto_sucio)
    tel_detectado = telefonos[0] if telefonos else ""
    
    # 2. Intentar separar Nombre y Dirección (Lógica por posición)
    # Normalmente el nombre está al inicio de la nota
    st.session_state.datos_form['n'] = resultados[0] if len(resultados) > 0 else ""
    st.session_state.datos_form['t'] = tel_detectado
    # La dirección suele ser lo que queda al final
    st.session_state.datos_form['d'] = resultados[-1] if len(resultados) > 1 else ""
    
    st.toast("✅ Análisis completado")

# --- INTERFAZ DE USUARIO ---
st.title("🛒 TropiExpress v11.0")
st.caption("Base de Datos y Registro Automático")

col1, col2 = st.columns([1, 1.2], gap="large")

with col1:
    st.subheader("📸 1. Escanear Nota")
    archivo = st.file_uploader("Subir foto del pedido", type=['jpg', 'jpeg', 'png'])
    
    if archivo:
        img = Image.open(archivo)
        st.image(img, use_container_width=True)
        
        if st.button("🔍 EXTRAER DATOS", use_container_width=True):
            with st.spinner("Leyendo manuscrito..."):
                extraer_datos_ocr(img)
                st.rerun()

with col2:
    st.subheader("📝 2. Confirmar y Guardar")
    with st.form("registro_pedido"):
        f_nombre = st.text_input("Nombre del Cliente", value=st.session_state.datos_form['n'])
        f_tel = st.text_input("WhatsApp (10 dígitos)", value=st.session_state.datos_form['t'])
        f_dir = st.text_input("Dirección de Entrega", value=st.session_state.datos_form['d'])
        
        # Botón de Guardado
        enviado = st.form_submit_button("📥 GUARDAR EN BASE DE DATOS", use_container_width=True)
        
        if enviado:
            if f_nombre and f_tel:
                # Limpiar teléfono para el link
                tel_limpio = "".join(filter(str.isdigit, f_tel))
                
                # Guardar en la lista
                nuevo_registro = {
                    "Fecha": datetime.now().strftime("%Y-%m-%d"),
                    "Hora": datetime.now().strftime("%H:%M"),
                    "Cliente": f_nombre,
                    "Telefono": tel_limpio,
                    "Direccion": f_dir
                }
                st.session_state.lista_pedidos.append(nuevo_registro)
                
                # Crear link de WhatsApp
                mensaje = f"Hola *{f_nombre}*, TropiExpress confirma tu pedido en *{f_dir}*."
                url_wa = f"https://wa.me/57{tel_limpio}?text={urllib.parse.quote(mensaje)}"
                
                st.success(f"¡{f_nombre} guardado!")
                st.markdown(f"[📲 ENVIAR WHATSAPP]({url_wa})")
                
                # Limpiar formulario
                st.session_state.datos_form = {'n': '', 't': '', 'd': ''}
            else:
                st.error("Faltan datos críticos.")

# --- SECCIÓN DE BASE DE DATOS ---
st.divider()
if st.session_state.lista_pedidos:
    st.subheader("📊 Base de Datos del Día")
    df = pd.DataFrame(st.session_state.lista_pedidos)
    
    # Mostrar tabla
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Botones de exportación
    col_a, col_b = st.columns(2)
    with col_a:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 DESCARGAR EXCEL (CSV)",
            data=csv,
            file_name=f"tropiexpress_{datetime.now().strftime('%d_%m')}.csv",
            mime='text/csv',
            use_container_width=True
        )
    with col_b:
        if st.button("🗑️ BORRAR TODO", use_container_width=True):
            st.session_state.lista_pedidos = []
            st.rerun()
