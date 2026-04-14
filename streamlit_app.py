import streamlit as st
import pandas as pd
import easyocr
import cv2
import numpy as np
from PIL import Image, ImageOps
from datetime import datetime
import re
import urllib.parse
import json
import io  # Importante para la manipulación de bytes en memoria
from openai import OpenAI

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TropiExpress v13.0 (Full IA)", page_icon="🛒", layout="wide")

# --- CONEXIÓN A DEEPSEEK ---
try:
    client = OpenAI(
        api_key=st.secrets["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com"
    )
except Exception as e:
    st.error(f"Error de configuración de IA: {e}")
    client = None

# --- CACHE DE OCR ---
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es'], gpu=False)

reader = load_ocr()

# --- ESTADO DE LA SESIÓN ---
if 'base_datos' not in st.session_state:
    st.session_state.base_datos = []
if 'temp_datos' not in st.session_state:
    st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}

# ==============================================================================
# --- NUEVA FUNCIÓN: COMPRESIÓN DE IMAGEN PARA EVITAR ERRORES DE MEMORIA ---
# ==============================================================================
def comprimir_imagen(archivo_subido, max_width=1000, max_height=1000, quality=70):
    """
    Toma un archivo subido, lo redimensiona y reduce su calidad para bajar los MB.
    """
    try:
        # 1. Abrir la imagen con PIL
        img = Image.open(archivo_subido)
        
        # 2. Corregir orientación basada en EXIF (importante para fotos de celular)
        img = ImageOps.exif_transpose(img)
        
        # 3. Obtener dimensiones actuales
        width, height = img.size
        
        # 4. Calcular el factor de escala manteniendo la relación de aspecto
        if width > max_width or height > max_height:
            if width > height:
                factor = max_width / width
            else:
                factor = max_height / height
            
            new_width = int(width * factor)
            new_height = int(height * factor)
            
            # 5. Redimensionar la imagen (LANCZOS es un buen filtro de alta calidad)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
        # 6. Guardar la imagen en un objeto de bytes en memoria
        buffer_bytes = io.BytesIO()
        
        # Convertir a RGB si está en RGBA para poder guardar como JPEG
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3]) # 3 es el canal alfa
            img = background
            
        img.save(buffer_bytes, format="JPEG", quality=quality, optimize=True)
        
        # 7. Convertir de nuevo a un objeto de PIL para el resto del procesamiento
        buffer_bytes.seek(0)
        img_comprimida = Image.open(buffer_bytes)
        
        #st.success(f"Imagen comprimida de {width}x{height} a {img_comprimida.size[0]}x{img_comprimida.size[1]}.")
        return img_comprimida

    except Exception as e:
        st.error(f"Error al comprimir la imagen: {e}")
        return None
# ==============================================================================

# --- FUNCIÓN MAESTRA: PROCESAMIENTO CON IA ---
def procesar_con_ia(texto_crudo):
    """
    Envía el texto crudo a DeepSeek y actualiza el estado con datos estructurados.
    """
    if not client:
        st.error("La API de DeepSeek no está vinculada.")
        return

    prompt = f"""
    Eres el gestor logístico de TropiExpress en Medellín. 
    Tu objetivo es recibir un texto desordenado (de voz o imagen) y devolver un JSON puro.

    REGLAS:
    1. "nombre": Nombre del cliente en formato Título.
    2. "telefono": Solo los 10 dígitos numéricos (celular de Colombia).
    3. "direccion": Dirección completa en MAYÚSCULAS, incluyendo detalles (Apto, Bloque, Interior).
    
    TEXTO A PROCESAR:
    {texto_crudo}

    RESPONDE SOLO EL OBJETO JSON:
    {{
      "nombre": "",
      "telefono": "",
      "direccion": ""
    }}
    """

    with st.spinner("DeepSeek procesando información..."):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Eres un extractor de datos ultra preciso para logística."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            contenido = response.choices[0].message.content.strip()
            limpio = re.search(r'\{.*\}', contenido, re.DOTALL)
            
            if limpio:
                datos = json.loads(limpio.group())
                st.session_state.temp_datos['n'] = datos.get('nombre', '')
                st.session_state.temp_datos['t'] = datos.get('telefono', '')
                st.session_state.temp_datos['d'] = datos.get('direccion', '')
                #st.success("¡Información extraída!")
            else:
                st.warning("No se pudo estructurar la información del texto.")

        except Exception as e:
            st.error(f"Error en la comunicación con la IA: {e}")

# --- PROCESAMIENTO DE IMAGEN ---
def pre_procesar_imagen(pil_image):
    # La imagen ya llega comprimida y redimensionada
    img = np.array(pil_image.convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return gray

def analizar_nota_ia(img_comprimida):
    # Ya no abrimos el archivo aquí, sino que recibimos la imagen PIL comprimida
    img_limpia = pre_procesar_imagen(img_comprimida)
    
    with st.spinner("Escaneando papel comprimido..."):
        resultados = reader.readtext(img_limpia, detail=0, paragraph=True)
        texto_ocr = " ".join(resultados)
        procesar_con_ia(texto_ocr)

# --- INTERFAZ DE USUARIO ---
st.title("🛒 TropiExpress v13.0 (IA Total)")

col_izq, col_der = st.columns([1, 1])

with col_izq:
    st.subheader("📥 Entrada de Datos")
    
    tab1, tab2 = st.tabs(["📸 Foto de Nota", "🎙️ Dictado / Texto"])
    
    with tab1:
        foto = st.file_uploader("Cargar imagen", type=['jpg', 'jpeg', 'png'])
        
        # Modificación en el flujo del botón: primero comprimir, luego analizar
        if foto and st.button("Analizar Imagen", use_container_width=True):
            with st.spinner("Bajando MB para que el celular no sufra..."):
                img_comprimida = comprimir_imagen(foto)
            
            if img_comprimida:
                analizar_nota_ia(img_comprimida)
                st.rerun()
            else:
                st.error("Hubo un problema al procesar la imagen.")
            
    with tab2:
        texto_libre = st.text_area("Pega el dictado o texto aquí:", placeholder="Ej: Pedido para Don Pedro 3201234567 Calle 45 #23-10 Belén")
        if st.button("Procesar con DeepSeek", use_container_width=True):
            if texto_libre:
                procesar_con_ia(texto_libre)
                st.rerun()

with col_der:
    st.subheader("📝 Verificación y Guardado")
    with st.form("formulario_ia"):
        nombre = st.text_input("Nombre del Cliente", value=st.session_state.temp_datos['n'])
        telefono = st.text_input("WhatsApp (10 dígitos)", value=st.session_state.temp_datos['t'])
        direccion = st.text_input("Dirección de Entrega", value=st.session_state.temp_datos['d'])
        
        btn_guardar = st.form_submit_button("✅ CONFIRMAR Y GUARDAR", use_container_width=True)
        
        if btn_guardar:
            if nombre and telefono:
                st.session_state.base_datos.append({
                    "Fecha": datetime.now().strftime("%d/%m %H:%M"),
                    "Cliente": nombre,
                    "Tel": telefono,
                    "Dir": direccion
                })
                st.session_state.temp_datos = {'n': '', 't': '', 'd': ''}
                st.success("¡Pedido registrado exitosamente!")
                st.rerun()
            else:
                st.error("Faltan datos críticos (Nombre o Teléfono).")

# --- VISUALIZACIÓN DE PEDIDOS ---
if st.session_state.base_datos:
    st.divider()
    st.subheader("📋 Pedidos del Día")
    df = pd.DataFrame(st.session_state.base_datos)
    
    def crear_link(row):
        texto_wa = f"Hola {row['Cliente']}, TropiExpress confirma tu pedido para entrega en: {row['Dir']}"
        encoded_msg = urllib.parse.quote(texto_wa)
        return f"https://wa.me/57{row['Tel']}?text={encoded_msg}"

    df['Acción'] = df.apply(crear_link, axis=1)
    
    st.dataframe(df, use_container_width=True, column_config={
        "Acción": st.column_config.LinkColumn("Enviar WhatsApp", display_text="📲 Abrir Chat")
    })
