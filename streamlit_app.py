import streamlit as st
import pandas as pd
from datetime import datetime
import json
import re
from openai import OpenAI

# --- CONFIGURACIÓN ULTRA LIGERA ---
st.set_page_config(page_title="TropiExpress v13.0", page_icon="🛒")

# Inicialización de estados
if 'temp_datos' not in st.session_state:
    st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}
if 'base_datos' not in st.session_state:
    st.session_state.base_datos = []

# --- CLIENTE DE IA (DeepSeek) ---
def conectar_ia():
    if "DEEPSEEK_API_KEY" not in st.secrets:
        st.error("Falta la llave DEEPSEEK_API_KEY en Secrets.")
        return None
    return OpenAI(
        api_key=st.secrets["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com"
    )

client = conectar_ia()

# --- FUNCIÓN DE PROCESAMIENTO ---
def procesar_texto(texto):
    if not client: return
    
    prompt = f"""
    Extrae Nombre, Teléfono (10 dígitos) y Dirección de este texto: "{texto}"
    Responde SOLO un JSON con las llaves: "nombre", "telefono", "direccion".
    Si no sabes algo, deja vacío "".
    """
    
    try:
        # Usamos un timeout para que no se quede pegado eternamente
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            timeout=15.0 
        )
        
        resultado = response.choices[0].message.content.strip()
        # Limpieza de JSON
        match = re.search(r'\{.*\}', resultado, re.DOTALL)
        if match:
            datos = json.loads(match.group())
            st.session_state.temp_datos['n'] = str(datos.get('nombre', '')).title()
            st.session_state.temp_datos['t'] = str(datos.get('telefono', ''))
            st.session_state.temp_datos['d'] = str(datos.get('direccion', '')).upper()
            return True
    except Exception as e:
        st.error(f"Error de conexión: {e}")
    return False

# --- INTERFAZ SIMPLIFICADA ---
st.title("🛒 TropiExpress IA")

# Área de entrada
st.subheader("🎙️ Dictado o Texto")
entrada = st.text_area("Pega el pedido aquí:", height=100, key="input_principal")

if st.button("PROCESAR PEDIDO 🚀", use_container_width=True):
    if entrada:
        with st.spinner("IA analizando..."):
            exito = procesar_texto(entrada)
            if exito:
                st.toast("¡Datos extraídos!", icon="✅")
                # No usamos st.rerun() aquí para evitar que se pierda el foco en móviles
            else:
                st.error("La IA no pudo procesar el texto. Revisa tu saldo o conexión.")
    else:
        st.warning("Escribe algo primero.")

st.divider()

# Formulario de Verificación
st.subheader("📝 Verificación")
with st.form("registro_pedido"):
    # Estos campos se llenan con el session_state
    nombre = st.text_input("Nombre", value=st.session_state.temp_datos['n'])
    telef = st.text_input("Teléfono", value=st.session_state.temp_datos['t'])
    direc = st.text_input("Dirección", value=st.session_state.temp_datos['d'])
    
    enviar = st.form_submit_button("✅ GUARDAR DEFINITIVO", use_container_width=True)
    
    if enviar:
        if nombre and telef:
            st.session_state.base_datos.append({
                "Cliente": nombre, "Tel": telef, "Dir": direc, "Hora": datetime.now().strftime("%H:%M")
            })
            st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}
            st.success("¡Guardado!")
            st.rerun()
        else:
            st.error("Nombre y Teléfono son obligatorios.")

# Tabla de resultados
if st.session_state.base_datos:
    st.write("### Pedidos Guardados")
    st.table(pd.DataFrame(st.session_state.base_datos))
