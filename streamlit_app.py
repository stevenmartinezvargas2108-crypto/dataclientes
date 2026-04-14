import streamlit as st
import pandas as pd
import easyocr
import cv2
import numpy as np
from PIL import Image, ImageOps
from datetime import datetime
import re
import urllib.parse
from openai import OpenAI  # Usamos la librería de OpenAI compatible con DeepSeek

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="TropiExpress v13.0 (IA)", page_icon="🛒", layout="wide")

# Configuración de la API de DeepSeek
# Asegúrate de añadir 'DEEPSEEK_API_KEY' en los Secrets de tu App en Streamlit Cloud
try:
    client = OpenAI(
        api_key=st.secrets["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com" # URL de la API de DeepSeek
    )
except Exception as e:
    st.error(f"Error de configuración de IA: {e}")
    client = None

@st.cache_resource
def load_ocr():
    # Mantenemos EasyOCR para leer el texto crudo de la imagen
    return easyocr.Reader(['es'], gpu=False)

reader = load_ocr()

if 'base_datos' not in st.session_state:
    st.session_state.base_datos = []
if 'temp_datos' not in st.session_state:
    st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}

# --- FUNCIÓN MAESTRA DE IA (DeepSeek) ---
def procesar_texto_con_ia(texto_crudo):
    """
    Toma cualquier texto y usa DeepSeek para extraer Nombre, Teléfono y Dirección.
    """
    if not client:
        st.error("La IA no está configurada.")
        return

    prompt = f"""
    Eres un asistente experto en logística para TropiExpress en Medellín, Colombia.
    Tu tarea es extraer información de pedidos a partir de texto crudo (que puede venir de OCR o dictado).
    
    INSTRUCCIONES:
    1. Analiza el siguiente texto crudo.
    2. Extrae el Nombre del Cliente (formato Título).
    3. Extrae el Número de Teléfono/WhatsApp (solo dígitos, sin espacios, debe tener 10 dígitos para Colombia).
    4. Extrae la Dirección Completa (incluyendo apartamento, bloque, etc., en MAYÚSCULAS).
    
    Si no encuentras un dato, déjalo en blanco ("").
    
    RESPONDE ÚNICAMENTE CON UN OBJETO JSON VÁLIDO CON ESTAS LLAVES:
    "nombre", "telefono", "direccion"
    
    TEXTO CRUDO A ANALIZAR:
    ---
    {texto_crudo}
    ---
    """

    with st.spinner("DeepSeek analizando el pedido..."):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Eres un extractor de datos JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1 # Temperatura baja para respuestas deterministas
            )
            
            respuesta_json = response.choices[0].message.content.strip()
            # A veces el modelo devuelve Markdown ```json ... ```, lo limpiamos
            respuesta_json = re.sub(r'```json\s*|```', '', respuesta_json)
            
            import json
            datos_extraidos = json.loads(respuesta_json)
            
            # Actualizar el estado temporal con lo extraído por la IA
            st.session_state.temp_datos['n'] = datos_extraidos.get('nombre', '').strip().title()
            # Limpiar teléfono de espacios y asegurar 10 dígitos
            tel = datos_extraidos.get('telefono', '')
            tel_limpio = re.sub(r'\D', '', tel) # Solo dígitos
            if len(tel_limpio) > 10: tel_limpio = tel_limpio[-10:] # Tomar últimos 10
            st.session_state.temp_datos['t'] = tel_limpio
            
            st.session_state.temp_datos['d'] = datos_extraidos.get('direccion', '').strip().upper()
            st.success("¡Pedido extraído con éxito por la IA!")

        except Exception as e:
            st.error(f"Error al conectar con DeepSeek: {e}")

# --- MEJORA 1: LIMPIEZA DE IMAGEN ---
def pre_procesar_imagen(pil_image):
    img = np.array(pil_image.convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.medianBlur(gray, 3) # Suavizado para quitar ruido
    processed_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return processed_img

def analizar_nota_ia(archivo):
    img_orig = Image.open(archivo)
    img_orig = ImageOps.exif_transpose(img_orig)
    img_orig.thumbnail((1200, 1200))
    
    img_limpia = pre_procesar_imagen(img_orig)
    
    with st.spinner("Leyendo imagen..."):
        # Mantenemos EasyOCR para la lectura inicial
        resultados = reader.readtext(img_limpia, detail=0, paragraph=True)
        texto_completo = " ".join(resultados)
        
        # --- EL CAMBIO CLAVE ---
        # En lugar de Regex, le pasamos todo el texto crudo a DeepSeek
        st.write(f"**Texto detectado por OCR (crudo):** {texto_completo}") # Opcional: para depurar
        procesar_texto_con_ia(texto_completo)

# --- INTERFAZ ---
st.title("🛒 TropiExpress v13.0 (IA DeepSeek)")

c1, c2 = st.columns([1, 1.2])

with c1:
    st.subheader("📸 Escáner de Notas")
    foto = st.file_uploader("Subir nota", type=['jpg', 'png', 'jpeg'])
    if foto:
        if st.button("🚀 TRATAR Y LEER CON IA", use_container_width=True):
            analizar_nota_ia(foto)
            st.rerun()
            
    st.divider()
    st.subheader("🎙️ Dictado Inteligente")
    st.write("Dí cualquier cosa: 'Enviar a Carlos en la Cra 50, su cel es 310...'")
    # Este campo es donde pegas el dictado del teclado del celular
    voz_input = st.text_area("Pega aquí el texto dictado:", 
                             placeholder="Ej: El pedido es para Doña Gloria Cel 300 Dirección Calle 10 # 5-10 Apto 201")
    if st.button("🪄 PROCESAR DICTADO CON IA"):
        if voz_input:
            # --- EL MISMO CAMBIO CLAVE ---
            # Usamos la misma función de IA para el dictado
            procesar_texto_con_ia(voz_input)
            st.rerun()
        else:
            st.warning("Por favor, pega un texto primero.")

with c2:
    st.subheader("📝 Verificación")
    # Los campos se autocompletarán con lo que DeepSeek extraiga
    with st.form("registro_v130"):
        c_nom = st.text_input("Nombre", value=st.session_state.temp_datos['n'])
        c_tel = st.text_input("WhatsApp (10 dígitos)", value=st.session_state.temp_datos['t'])
        c_dir = st.text_input("Dirección", value=st.session_state.temp_datos['d'])
        
        if st.form_submit_button("✅ GUARDAR PEDIDO", use_container_width=True):
            if c_nom and len(c_tel) == 10:
                st.session_state.base_datos.append({
                    "Fecha": datetime.now().strftime("%d/%m"),
                    "Cliente": c_nom, "Tel": c_tel, "Dir": c_dir
                })
                st.success(f"Pedido de {c_nom} guardado.")
                st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}
                st.rerun()
            else:
                st.error("Nombre y Teléfono (10 dígitos) son obligatorios.")

# --- TABLA ---
if st.session_state.base_datos:
    st.divider()
    df = pd.DataFrame(st.session_state.base_datos)
    
    # Crear link de WhatsApp funcional
    df['Link'] = df['Tel'].apply(lambda x: f"https://wa.me/57{x}" if x else "")
    
    # Mostrar tabla con links clickeables
    st.dataframe(df, use_container_width=True, column_config={
        "Link": st.column_config.LinkColumn("Enviar WA")
    })
    
    # Botón rápido para el último registro
    ultimo = st.session_state.base_datos[-1]
    msg = urllib.parse.quote(f"Hola {ultimo['Cliente']}, TropiExpress confirma tu pedido a {ultimo['Dir']}.")
    st.link_button(f"📲 Contactar a {ultimo['Cliente']}", f"https://wa.me/57{ultimo['Tel']}?text={msg}")
