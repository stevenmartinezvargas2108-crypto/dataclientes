import streamlit as st
import sqlite3
import pandas as pd
import easyocr
import numpy as np
from PIL import Image, ImageOps
import re

# Configuración Anti-Errores
st.set_page_config(page_title="Tropiexpress Admin", page_icon="🛒")
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# --- BASE DE DATOS MEJORADA ---
def get_db():
    conn = sqlite3.connect('tropiexpress_v5.db', check_same_thread=False)
    # Agregamos UNIQUE al telefono para evitar duplicados reales
    conn.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, nombre TEXT, direccion TEXT, telefono TEXT UNIQUE)''')
    return conn

@st.cache_resource
def load_reader():
    return easyocr.Reader(['es'], gpu=False)

db = get_db()
reader = load_reader()

st.title("🛒 Registro Tropiexpress")

tab1, tab2 = st.tabs(["📝 Nuevo / Actualizar", "📋 Listado"])

with tab1:
    foto = st.file_uploader("Capturar foto de datos", type=['jpg', 'jpeg', 'png'])
    n_sug, d_sug, t_sug = "", "", ""

    if foto:
        img = Image.open(foto)
        # --- MEJORA DE IMAGEN ---
        # Reducimos tamaño para no agotar la RAM y mejorar velocidad
        img.thumbnail((800, 800)) 
        # Convertimos a escala de grises para mejor contraste de IA
        gray_img = ImageOps.grayscale(img)
        st.image(img, caption="Foto procesada", width=300)
        
        if st.button("🔍 Escanear Datos"):
            with st.spinner("Analizando..."):
                res = reader.readtext(np.array(gray_img))
                texto_completo = " ".join([r[1] for r in res])
                
                # Buscar teléfono (10 dígitos)
                tel_find = re.search(r'\d{10}', texto_completo.replace(" ", ""))
                if tel_find: t_sug = tel_find.group()
                
                # Lógica simple para nombre (primera línea detectada)
                if res: n_sug = res[0][1]

    with st.form("registro"):
        tel = st.text_input("WhatsApp (Sin el 57)", value=t_sug)
        nom = st.text_input("Nombre del Cliente", value=n_sug)
        dir_entrega = st.text_input("Dirección de Entrega")
        
        if st.form_submit_button("✅ Guardar Cliente"):
            if tel and nom:
                try:
                    # Intenta insertar, si el teléfono existe (UNIQUE), falla y va al except
                    db.execute("INSERT INTO clientes (nombre, direccion, telefono) VALUES (?,?,?)", 
                               (nom, dir_entrega, tel))
                    db.commit()
                    st.success(f"NUEVO CLIENTE: {nom} guardado.")
                except sqlite3.IntegrityError:
                    # Si ya existe el teléfono, actualizamos los datos existentes
                    db.execute("UPDATE clientes SET nombre=?, direccion=? WHERE telefono=?", 
                               (nom, dir_entrega, tel))
                    db.commit()
                    st.warning(f"CLIENTE ACTUALIZADO: Los datos de {nom} han sido refrescados.")
                
                # Link de Bienvenida
                link = f"https://wa.me/57{tel}?text=Hola%20{nom},%20tu%20registro%20en%20Tropiexpress%20está%20listo!"
                st.markdown(f"[📲 Enviar WhatsApp a {nom}]({link})")

with tab2:
    if st.button("🔄 Actualizar Tabla"):
        df = pd.read_sql_query("SELECT * FROM clientes", db)
        st.dataframe(df, use_container_width=True)
