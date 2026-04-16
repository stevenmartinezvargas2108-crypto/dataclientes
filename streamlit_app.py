import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from streamlit_mic_recorder import mic_recorder
import pandas as pd
import re
import urllib.parse
from datetime import datetime
from PIL import Image
import io
import json

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tropiexpress Master", page_icon="🛒", layout="wide")

# --- 2. INICIALIZACIÓN DE CONEXIONES Y MODELOS ---

# Configurar Gemini
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Usamos flash para rapidez en extracción
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    st.error(f"Error configurando Gemini API Key: {e}")
    st.stop()

# Conectar a Google Sheets (Usando el link público/editor de los Secrets)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error conectando a Google Sheets. Revisa el link en Secrets. Error: {e}")
    st.stop()

# Inicializar estado de la sesión para editar datos
if 'temp_datos' not in st.session_state:
    st.session_state['temp_datos'] = {'nombre': '', 'tel': '', 'dir': ''}

# --- 3. FUNCIONES LÓGICAS (IA Y DATOS) ---

def extraer_datos_ia(contenido, tipo="imagen"):
    """Usa Gemini para extraer datos de imagen o audio."""
    prompt = """
    Analiza el contenido adjunto (imagen de nota o audio).
    Extrae el NOMBRE COMPLETO del cliente, su TELÉFONO y su DIRECCIÓN de entrega.
    Si es audio, el cliente puede estar dictando los datos.
    Responde ÚNICAMENTE con un objeto JSON con este formato:
    {"nombre": "...", "tel": "...", "dir": "..."}
    Si no encuentras un dato, deja el valor vacío "".
    """
    try:
        if tipo == "imagen":
            img = Image.open(io.BytesIO(contenido))
            response = model.generate_content([prompt, img])
        elif tipo == "audio":
            audio_part = {"mime_type": "audio/wav", "data": contenido}
            response = model.generate_content([prompt, audio_part])
        
        # Limpiar la respuesta para obtener solo el JSON
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
    except Exception as e:
        st.error(f"Error en la extracción con IA ({tipo}): {e}")
        return None

# --- 4. INTERFAZ DE USUARIO ---
st.title("🛒 Tropiexpress Master Management")
st.markdown("---")

# Zona de Entrada (Imagen y Audio)
col_ingreso, col_formulario = st.columns([1, 1])

with col_ingreso:
    st.subheader("📸 Entrada de Datos")
    
    # --- ENTRADA POR IMAGEN ---
    archivo = st.file_uploader("Subir foto de nota de venta", type=['jpg', 'jpeg', 'png'], key="uploader_nota")
    
    if archivo:
        bytes_data = archivo.getvalue()
        st.image(bytes_data, caption="Nota cargada", use_container_width=True)
        if st.button("🚀 ANALIZAR IMAGEN CON IA", use_container_width=True):
            with st.spinner("Gemini leyendo la nota..."):
                datos = extraer_datos_ia(bytes_data, tipo="imagen")
                if datos:
                    # Guardar en session_state para el formulario
                    st.session_state['temp_datos'] = {
                        'nombre': datos.get('nombre', '').title(),
                        'tel': re.sub(r'\D', '', str(datos.get('tel', ''))), # Solo números
                        'dir': datos.get('dir', '')
                    }
                    st.toast("Datos extraídos de la imagen", icon="📸")
                    st.rerun()

    st.markdown("---")
    
    # --- ENTRADA POR AUDIO (RESPALDO) ---
    st.subheader("🎙️ Respaldo por Voz")
    st.write("Si la imagen no es clara, dicta: 'Nombre: [Juan], Teléfono: [300...], Dirección: [Calle...]'")
    
    # Grabadora de audio
    audio_grabado = mic_recorder(
        start_prompt="Empezar a dictar 🎙️",
        stop_prompt="Parar y procesar ⏹️",
        key='grabadora_tropi'
    )

    if audio_grabado:
        with st.spinner("Gemini escuchando el dictado..."):
            datos_audio = extraer_datos_ia(audio_grabado['bytes'], tipo="audio")
            if datos_audio:
                # Actualizar session_state (solo si el audio trajo datos)
                if datos_audio.get('nombre') or datos_audio.get('tel'):
                    st.session_state['temp_datos'] = {
                        'nombre': datos_audio.get('nombre', st.session_state['temp_datos']['nombre']).title(),
                        'tel': re.sub(r'\D', '', str(datos_audio.get('tel', st.session_state['temp_datos']['tel']))),
                        'dir': datos_audio.get('dir', st.session_state['temp_datos']['dir'])
                    }
                    st.toast("Datos actualizados por audio", icon="🎙️")
                    st.rerun()


# Zona de Confirmación y Guardado
with col_formulario:
    st.subheader("📝 Confirmar y Guardar Registro")
    
    # formulario vinculado al session_state para permitir edición
    with st.form("form_cliente", clear_on_submit=False):
        f_nom = st.text_input("Nombre Completo", value=st.session_state['temp_datos']['nombre'])
        f_tel = st.text_input("Teléfono / WhatsApp (10 dígitos)", value=st.session_state['temp_datos']['tel'])
        f_dir = st.text_input("Dirección de Entrega", value=st.session_state['temp_datos']['dir'])
        f_promo = st.selectbox("Estrategia", ["Bienvenida Tropiexpress 🏠", "Envío Gratis 🚚", "Bono $5.000 🎁", "Cliente Frecuente ⭐"])
        
        btn_guardar = st.form_submit_button("✅ VERIFICAR Y GUARDAR EN LA NUBE", use_container_width=True)
        
        if btn_guardar:
            if f_nom and f_tel and len(f_tel) >= 10:
                with st.spinner("Conectando a la nube y verificando duplicados..."):
                    
                    # 1. LEER DATOS ACTUALES DE LA NUBE (para validar)
                    # Forzamos la lectura fresca
                    df_nube = conn.read(ttl="1s") 
                    
                    # Limpiar teléfonos antiguos para comparar (asegurar que sean strings)
                    telefonos_registrados = df_nube['Telefono'].astype(str).tolist()
                    
                    # 2. VALIDACIÓN DE DUPLICADOS
                    if f_tel in telefonos_registrados:
                        st.error(f"❌ ERROR: El cliente con teléfono {f_tel} ya está registrado en la base de datos.")
                        
                        # Buscar el nombre del cliente existente para referencia
                        cliente_existente = df_nube[df_nube['Telefono'].astype(str) == f_tel]['Nombre'].values[0]
                        st.info(f"Ese número pertenece a: *{cliente_existente}*")
                        
                    else:
                        # 3. GUARDAR NUEVO CLIENTE
                        fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
                        
                        # Crear el DataFrame de la nueva fila
                        nuevo_df = pd.DataFrame([{
                            "Fecha": fecha_hoy,
                            "Nombre": f_nom,
                            "Telefono": f_tel,
                            "Direccion": f_dir,
                            "Estrategia": f_promo
                        }])
                        
                        # Concatenar el nuevo con el existente
                        df_actualizado = pd.concat([df_nube, nuevo_df], ignore_index=True)
                        
                        # Actualizar la hoja de cálculo completa
                        conn.update(data=df_actualizado)
                        
                        st.success(f"🎉 ¡{f_nom} guardado correctamente en Google Sheets!")
                        
                        # Limpiar formulario
                        st.session_state['temp_datos'] = {'nombre': '', 'tel': '', 'dir': ''}
                        
                        # 4. GENERAR WHATSAPP DE BIENVENIDA
                        wa_num = f"57{f_tel}" # Prefijo Colombia
                        msg = f"Bienvenido a Tropiexpress {f_nom} 🛒. Confirmamos tu pedido en la dirección: {f_dir}. Tu regalo de bienvenida es: {f_promo}."
                        link_wa = f"https://wa.me/{wa_num}?text={urllib.parse.quote(msg)}"
                        
                        st.markdown(f'''
                            <a href="{link_wa}" target="_blank" style="text-decoration:none;">
                                <div style="background-color:#25D366;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;font-size:18px;margin-top:10px;">
                                    📲 ENVIAR BIENVENIDA POR WHATSAPP
                                </div>
                            </a>
                        ''', unsafe_allow_html=True)
                        st.rerun()

            else:
                st.warning("Nombre y Teléfono (mínimo 10 dígitos) son obligatorios.")

# --- 5. VISUALIZACIÓN DE LA BASE DE DATOS ---
st.markdown("---")
st.subheader("📋 Registro Reciente de Clientes (Nube)")

# Botón para forzar recarga
if st.button("🔄 Actualizar Tabla"):
    st.rerun()

try:
    # Leer datos frescos
    df_ver = conn.read(ttl="5s")
    # Mostrar los últimos 10 (invertidos para ver el más nuevo arriba)
    st.dataframe(df_ver.iloc[::-1].head(10), use_container_width=True)
except:
    st.info("Aún no hay datos registrados en la hoja de cálculo.")
