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
            
            # Limpieza de respuesta para asegurar JSON puro
            contenido = response.choices[0].message.content.strip()
            limpio = re.search(r'\{.*\}', contenido, re.DOTALL)
            
            if limpio:
                datos = json.loads(limpio.group())
                st.session_state.temp_datos['n'] = datos.get('nombre', '')
                st.session_state.temp_datos['t'] = datos.get('telefono', '')
                st.session_state.temp_datos['d'] = datos.get('direccion', '')
                st.success("¡Información extraída!")
            else:
                st.warning("No se pudo estructurar la información del texto.")

        except Exception as e:
            st.error(f"Error en la comunicación con la IA: {e}")

# --- PROCESAMIENTO DE IMAGEN ---
def pre_procesar_imagen(pil_image):
    img = np.array(pil_image.convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # Mejoramos contraste para que EasyOCR capture más texto para la IA
    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return gray

def analizar_nota_ia(archivo):
    img_orig = Image.open(archivo)
    img_orig = ImageOps.exif_transpose(img_orig)
    img_limpia = pre_procesar_imagen(img_orig)
    
    with st.spinner("Escaneando papel..."):
        resultados = reader.readtext(img_limpia, detail=0, paragraph=True)
        texto_ocr = " ".join(resultados)
        # La IA se encarga de arreglar los errores del OCR
        procesar_con_ia(texto_ocr)

# --- INTERFAZ DE USUARIO ---
st.title("🛒 TropiExpress v13.0 (IA Total)")

col_izq, col_der = st.columns([1, 1])

with col_izq:
    st.subheader("📥 Entrada de Datos")
    
    tab1, tab2 = st.tabs(["📸 Foto de Nota", "🎙️ Dictado / Texto"])
    
    with tab1:
        foto = st.file_uploader("Cargar imagen", type=['jpg', 'jpeg', 'png'])
        if foto and st.button("Analizar Imagen", use_container_width=True):
            analizar_nota_ia(foto)
            st.rerun()
            
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
                # Limpiar después de guardar
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
    
    # Link de WhatsApp con mensaje automático
    def crear_link(row):
        texto_wa = f"Hola {row['Cliente']}, TropiExpress confirma tu pedido para entrega en: {row['Dir']}"
        encoded_msg = urllib.parse.quote(texto_wa)
        return f"https://wa.me/57{row['Tel']}?text={encoded_msg}"

    df['Acción'] = df.apply(crear_link, axis=1)
    
    st.dataframe(df, use_container_width=True, column_config={
        "Acción": st.column_config.LinkColumn("Enviar WhatsApp", display_text="📲 Abrir Chat")
    })
