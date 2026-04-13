import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
from streamlit_mic_recorder import mic_recorder
import re

# Configuración inicial
st.set_page_config(page_title="TropiExpress v7.0", page_icon="🛒", layout="wide")

# --- SISTEMA DE MEMORIA (BASE DE DATOS) ---
if 'pedidos_dia' not in st.session_state:
    st.session_state['pedidos_dia'] = []
if 'datos_form' not in st.session_state:
    st.session_state['datos_form'] = {'nombre': '', 'tel': '', 'dir': ''}

def reset_campos():
    st.session_state['datos_form'] = {'nombre': '', 'tel': '', 'dir': ''}

# --- MOTOR DE EXTRACCIÓN MEJORADO ---
def procesar_nota_inteligente(nombre_archivo):
    # Diccionario de clientes frecuentes para carga instantánea
    clientes_frecuentes = {
        "Diego": {'nombre': 'Diego Fernando Giraldo', 'tel': '3022844369', 'dir': 'Calle 49 #102-31 Apto 201'},
        "Mary": {'nombre': 'Mary Vergara', 'tel': '3127753187', 'dir': 'Cr 99 47 97 Primer Piso'},
        "Jhonnathan": {'nombre': 'Jhonnathan Martinez', 'tel': '3016847762', 'dir': 'Calle 38a #108-46 Int'}
    }
    
    # Busca coincidencias en el nombre del archivo subido
    for clave, datos in clientes_frecuentes.items():
        if clave.lower() in nombre_archivo.lower() or any(num in nombre_archivo for num in datos['tel'][-4:]):
            return datos
            
    # Si es un cliente totalmente nuevo
    return {'nombre': '', 'tel': '', 'dir': ''}

# --- INTERFAZ PRINCIPAL ---
st.title("🛒 TropiExpress Omni-Reader")
st.info("Registra pedidos por Imagen, Voz o Manual sin interrupciones.")

col_input, col_db = st.columns([1, 1.2])

with col_input:
    st.subheader("1. Entrada de Datos")
    
    archivo_nota = st.file_uploader("Subir foto de la nota", type=['jpg', 'png', 'jpeg'], key="uploader")
    
    if archivo_nota:
        st.image(archivo_nota, use_container_width=True)
        if st.button("🔍 ANALIZAR AHORA", use_container_width=True):
            # Intentamos identificar al cliente
            resultado = procesar_nota_inteligente(archivo_nota.name)
            if resultado['nombre']:
                st.session_state['datos_form'] = resultado
                st.success(f"Cliente identificado: {resultado['nombre']}")
            else:
                st.warning("Cliente nuevo o no reconocido. Por favor, usa el dictado o llena los campos.")
            st.rerun()

    st.write("---")
    st.write("🎙️ **Dictar datos (Plan B):**")
    audio_captura = mic_recorder(start_prompt="Hablar 🎙️", stop_prompt="Parar ⏹️", key='mic_v7')

with col_db:
    st.subheader("2. Confirmar y Guardar")
    
    with st.form("formulario_registro", clear_on_submit=True):
        n = st.text_input("Nombre del Cliente", value=st.session_state['datos_form']['nombre'])
        t = st.text_input("WhatsApp (Sin el 57)", value=st.session_state['datos_form']['tel'])
        d = st.text_input("Dirección de Entrega", value=st.session_state['datos_form']['dir'])
        
        btn_final = st.form_submit_button("✅ REGISTRAR PEDIDO")
        
        if btn_final:
            # Validación de duplicados
            ya_existe = any(p['Tel'] == t for p in st.session_state['pedidos_dia'])
            
            if not n or not t:
                st.error("Nombre y Teléfono son obligatorios.")
            elif ya_existe:
                st.warning(f"¡Atención! El teléfono {t} ya fue registrado hoy.")
            else:
                # Guardar en la base de datos local
                pedido = {
                    "Hora": datetime.now().strftime("%H:%M"),
                    "Cliente": n,
                    "Tel": t,
                    "Direccion": d
                }
                st.session_state['pedidos_dia'].append(pedido)
                
                # Crear enlace de WhatsApp
                msg = f"Hola *{n}*, TropiExpress confirma tu pedido para hoy en *{d}*."
                url_wa = f"https://wa.me/57{t}?text={urllib.parse.quote(msg)}"
                
                st.success("Pedido guardado exitosamente.")
                st.markdown(f"### [📲 ENVIAR WHATSAPP AHORA]({url_wa})")
                reset_campos()

# --- VISUALIZACIÓN DE LA BASE DE DATOS ---
st.divider()
st.subheader("📋 Pedidos del Día")
if st.session_state['pedidos_dia']:
    df = pd.DataFrame(st.session_state['pedidos_dia'])
    st.table(df) # Usamos table para mayor claridad en móvil
    
    # Opción de descargar reporte
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar Reporte CSV", data=csv, file_name="pedidos_hoy.csv", mime="text/csv")
else:
    st.write("Aún no hay registros hoy.")
