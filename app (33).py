import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import pandas as pd
import io
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Procesador Masivo Contenedores", layout="wide")



# --- LÓGICA DE IA ---
def analizar_imagen(image, key):
    # Configurar la API con la clave que ingresó el usuario
    genai.configure(api_key=key)
    
    # ACTUALIZACIÓN: Usamos el modelo que sí tienes disponible
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = """
    Actúa como un sistema OCR experto en logística. Analiza la imagen del contenedor.
    Extrae estrictamente en formato JSON los siguientes campos:
    - sigla (ej: TRHU)
    - numero (ej: 496448)
    - dv (dígito verificador, ej: 9)
    - max_gross_kg (solo el numero)
    - tara_kg (solo el numero)
    
    Si un valor no es legible, pon null. No des explicaciones, solo el JSON.
    """
    
    try:
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        # Devolvemos el error como texto para verlo en el excel si falla
        return f"Error API: {e}"

def limpiar_json(texto):
    """Limpia la respuesta para obtener solo el JSON válido"""
    try:
        # A veces la IA devuelve texto antes o después del JSON, esto lo limpia
        json_str = texto.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
            
        return json.loads(json_str)
    except:
        return None

# --- INTERFAZ PRINCIPAL ---
st.title("📂 Procesamiento Masivo de Contenedores a Excel")
st.write("Sube una carpeta de fotos y obtén el Excel consolidado.")

# Verificar si hay API Key


# Carga de Archivos
uploaded_files = st.file_uploader(
    "Selecciona las fotos de los contenedores", 
    type=['png', 'jpg', 'jpeg', 'webp'], 
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"📸 {len(uploaded_files)} imágenes cargadas. Listo para procesar.")
    
    if st.button("🚀 Iniciar Procesamiento Masivo"):
        
        resultados = []
        barra_progreso = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            # Barra de progreso
            progreso = (i + 1) / len(uploaded_files)
            barra_progreso.progress(progreso)
            status_text.markdown(f"**Procesando:** `{uploaded_file.name}` ({i+1}/{len(uploaded_files)})")
            
            try:
                img = Image.open(uploaded_file)
                
                # 1. Llamar a la IA
                texto_respuesta = analizar_imagen(img, st.secrets["GEMINI_KEY"])
                
                # 2. Convertir respuesta a datos útiles
                datos = limpiar_json(texto_respuesta)
                
                if datos:
                    datos['archivo_origen'] = uploaded_file.name
                    datos['status'] = 'OK'
                    resultados.append(datos)
                else:
                    # Si falla la conversión a JSON, guardamos el error
                    resultados.append({
                        'archivo_origen': uploaded_file.name,
                        'status': 'Error Lectura IA',
                        'raw_text': texto_respuesta # Guardamos lo que dijo la IA para depurar
                    })
                    
            except Exception as e:
                resultados.append({
                    'archivo_origen': uploaded_file.name,
                    'status': f'Error Sistema: {str(e)}',
                })
            
            # Pausa breve para estabilidad
            time.sleep(4)

        status_text.text("✅ ¡Procesamiento finalizado!")
        st.balloons()
        
        # --- GENERAR EXCEL ---
        if resultados:
            df = pd.DataFrame(resultados)
            
            # Ordenar columnas estéticamente
            cols_first = ['archivo_origen', 'status', 'sigla', 'numero', 'dv', 'max_gross_kg', 'tara_kg']
            cols = cols_first + [c for c in df.columns if c not in cols_first]
            # Filtrar columnas para evitar errores si alguna no existe
            cols = [c for c in cols if c in df.columns]
            df = df[cols]
            
            st.divider()
            st.subheader("📊 Resultados")
            st.dataframe(df)
            
            # Preparar descarga
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
                
            st.download_button(
                label="📥 Descargar Excel Completo",
                data=buffer.getvalue(),
                file_name="reporte_contenedores.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"

            )





