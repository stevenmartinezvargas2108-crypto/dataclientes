import streamlit as st
from groq import Groq
import json
import urllib.parse
import re
import pandas as pd
import base64
from datetime import datetime
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIGURACIÓN DE MODELOS (Estrategia Anti-Errores) ---
# Lista de modelos de visión en orden de prioridad
MODELOS_VISION_DISPONIBLES = [
    "llama-3.2-11b-vision-instant",
    "llama-3.2-90b-vision-instant",
    "llama-3.2-11b-vision-preview"
]
MODELO_VOZ = "whisper-large-v3-turbo"

try:
    API_KEY = st.secrets["GROQ_API_KEY"]
except:
    API_KEY = ""

client = Groq(api_key=API_KEY)

st.set_page_config(page_title="Tropiexpress Ultra-AI", page_icon="🛒", layout="wide")

# Inicializar base de datos en la sesión del navegador
if 'db_clientes' not in st.session_state:
    st.session_state['db_clientes'] = []

# --- 2. FUNCIONES DE INTELIGENCIA ARTIFICIAL ---

def transcribir_audio(audio_bytes):
    """Convierte voz a texto usando Whisper"""
    try:
        file_tuple = ("audio.wav", audio_bytes, "audio/wav")
        transcription = client.audio.transcriptions.create(
            file=file_tuple,
            model=MODELO_VOZ,
            language="es"
        )
        return transcription.text
    except Exception as e:
        st.error(f"Error en dictado: {e}")
        return ""

def analizar_con_groq(imagen_bytes):
    """Analiza la imagen intentando varios modelos si uno falla"""
    base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
    
    for modelo in MODELOS_VISION_DISPONIBLES:
        try:
            completion = client.chat.completions.create(
                model=modelo,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extrae: nombre, tel, dir. Responde solo JSON: {'nombre': '...', 'tel': '...', 'dir': '...'}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }],
                response_format={"type": "json_object"}
            )
            res = json.loads(completion.choices[0].message.content)
            # Limpiar teléfono: solo dejar números
            if res.get('tel'):
                res['tel'] = re.sub(r'\D', '', str(res['tel']))
            return res
        except Exception as e:
            # Si el error es que el modelo no existe, intenta el siguiente de la lista
            if "model_decommissioned" in str(e) or "404" in str(e):
                continue
            else:
                st.error(f"Error técnico: {e}")
                return None
    
    st.error("No se pudo conectar con ningún modelo de visión de Groq.")
    return None

# --- 3. INTERFAZ DE USUARIO ---

st.title("🛒 Tropiexpress Ultra-Extract v3")
st.markdown("---")

archivo = st.file_uploader("📸 Sube o toma una foto de la nota", type=['jpg', 'jpeg', 'png'])

col1, col2 = st.columns([1, 1])

if archivo:
    bytes_data = archivo.getvalue()
    
    with col1:
        st.image(bytes_data, caption="Nota cargada", use_container_width=True)
        if st.button("🚀 PROCESAR IMAGEN", use_container_width=True):
            with st.spinner("Analizando con IA..."):
                res = analizar_con_groq(bytes_data)
                if res:
                    st.session_state['temp_datos'] = res
                    # Verificar Duplicados
                    tel_nuevo = res.get('tel', '')
                    if any(c['Tel'] == tel_nuevo for c in st.session_state['db_clientes']):
                        st.warning(f"⚠️ EL TELÉFONO {tel_nuevo} YA EXISTE EN LA BASE DE DATOS")
                    else:
                        st.success("✅ CLIENTE NUEVO")

    with col2:
        st.subheader("📝 Confirmación de Datos")
        datos = st.session_state.get('temp_datos', {'nombre': '', 'tel': '', 'dir': ''})
        
        # Microfono para correcciones rápidas
        st.write("🎙️ *Dictar corrección:*")
        audio_dictado = mic_recorder(start_prompt="Hablar 🎙️", stop_prompt="Detener ⏹️", key='dictador')
        
        if audio_dictado:
            texto = transcribir_audio(audio_dictado['bytes'])
            if texto:
                st.info(f"Escuché: {texto}")

        # Formulario de Registro
        with st.form("registro_cliente"):
            nom = st.text_input("Nombre del Cliente", value=datos.get('nombre', ''))
            tel = st.text_input("Teléfono (10 dígitos)", value=datos.get('tel', ''))
            dire = st.text_input("Dirección de Entrega", value=datos.get('dir', ''))
            promo = st.selectbox("Estrategia de Bienvenida", ["Envío Gratis 🚚", "Bono $5.000 🎁", "Cliente Frecuente ⭐"])
            
            submit = st.form_submit_button("✅ GUARDAR Y GENERAR WHATSAPP", use_container_width=True)
            
            if submit:
                # 1. Guardar en memoria
                nuevo_registro = {
                    "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Cliente": nom,
                    "Tel": tel,
                    "Dir": dire,
                    "Promo": promo
                }
                st.session_state['db_clientes'].append(nuevo_registro)
                
                # 2. Crear Link de WhatsApp
                wa_num = f"57{tel}" if len(tel) == 10 else tel
                msg = f"Hola {nom} 🛒, Tropiexpress confirma tu pedido.\n📍 Dirección: {dire}\n🎁 Regalo: {promo}"
                link = f"https://wa.me/{wa_num}?text={urllib.parse.quote(msg)}"
                
                st.markdown(f'''
                    <a href="{link}" target="_blank">
                        <div style="background-color:#25D366;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;font-size:18px;margin-top:10px;">
                            📲 ENVIAR BIENVENIDA POR WHATSAPP
                        </div>
                    </a>
                ''', unsafe_allow_html=True)

# --- 4. TABLA DE REGISTROS Y EXPORTACIÓN ---
st.markdown("---")
if st.session_state['db_clientes']:
    st.subheader("📋 Historial de Clientes Registrados")
    df = pd.DataFrame(st.session_state['db_clientes'])
    
    # Mostrar tabla (últimos primero)
    st.dataframe(df.iloc[::-1], use_container_width=True)
    
    # Botones de descarga
    c1, c2 = st.columns(2)
    with c1:
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Descargar CSV", csv, "clientes_tropiexpress.csv", "text/csv", use_container_width=True)
    with c2:
        # Generar Excel en memoria
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Pedidos')
        st.download_button("📊 Descargar Excel", output.getvalue(), "pedidos.xlsx", use_container_width=True)
