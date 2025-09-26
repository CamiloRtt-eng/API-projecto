import streamlit as st
import pandas as pd
import datetime
import os
import requests
from PIL import Image
import base64
import csv

LOGO_PATH = 'C:/Users/b12s306/Desktop/API projecto/logo_fiscalia.png'
DENUNCIAS_PATH = 'denuncias_registradas.csv'

def get_image_base64(path):
    import os
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as img_file:
        import base64
        return base64.b64encode(img_file.read()).decode()

st.set_page_config(page_title='Sistema Judicial SPOA', page_icon='⚖️', layout='centered')

logo_base64 = get_image_base64(LOGO_PATH)

st.markdown("""
<style>
.titulo-logo {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 32px;
    margin-bottom: 24px;
}
.titulo-logo img {
    height: 80px;
}
.titulo-logo-text {
    font-size: 2.2rem;
    font-weight: bold;
    color: #1a237e;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

if logo_base64:
    st.markdown(f"""
    <div class="titulo-logo">
        <img src="data:image/png;base64,{logo_base64}" alt="Logo Fiscalía" />
        <div class="titulo-logo-text">
            ⚖️ Sistema Judicial SPOA<br>
            <span style='font-size:1.2rem;font-weight:normal;'>Bienvenido al sistema de gestión de denuncias judiciales</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="titulo-logo">
        <div class="titulo-logo-text">
            ⚖️ Sistema Judicial SPOA<br>
            <span style='font-size:1.2rem;font-weight:normal;'>Bienvenido al sistema de gestión de denuncias judiciales</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Elimina los estilos y el contenedor con reborde

# Cargar datos
@st.cache_data
def cargar_datos(path):
    return pd.read_csv(path)

DATA_PATH = 'data/spoa.csv'
df = cargar_datos(DATA_PATH)

with st.sidebar:
    st.header('🔐 Autenticación Gemini')
    api_key = st.text_input('Clave API de Gemini', type='password')
    if api_key:
        st.success('Clave API ingresada.')
    else:
        st.info('Ingrese su clave API para conectar con Gemini.')

st.subheader('📄 Formulario de denuncia')
col1, col2 = st.columns(2)
with col1:
    fecha_denuncia = st.date_input('Fecha de denuncia', value=datetime.date.today())
    ciudad = st.text_input('Ciudad')
    localidad = st.text_input('Localidad de la ciudad')
    cantidad_agresores = st.number_input('Cantidad de agresores', min_value=1, step=1)
    asistencia_policial = st.radio('¿Se obtuvo asistencia policial?', ['Sí', 'No'])
with col2:
    delitos_disponibles = df['tipo_delito'].unique().tolist()
    delitos_seleccionados = st.multiselect('Delitos presentes en la denuncia', delitos_disponibles)
    tipo_arma = st.selectbox('Tipo de arma usada', ['No aplica', 'Arma blanca', 'Arma de fuego', 'Objeto contundente', 'Otro'])
descripcion = st.text_area('Descripción de la denuncia')

if st.button('Registrar denuncia'):
    if not delitos_seleccionados:
        st.error('Debe seleccionar al menos un delito.')
    else:
        st.success('Denuncia registrada correctamente.')
        # Filtrar delitos en spoa.csv
        casos = df[df['tipo_delito'].isin(delitos_seleccionados)]
        # Calcular tiempo estimado de condena por cada delito
        condenas = [f"{delito}: {penas[0] if len(penas)>0 else 'No encontrado'}" for delito in delitos_seleccionados if (penas := casos[casos['tipo_delito'] == delito]['pena_establecida'].unique())]
        # Calcular plazo para dictar sentencia (el menor plazo entre los delitos)
        limites = casos['limite_meses_dictar_pena'].astype(int).min() if not casos.empty else None
        if limites:
            fecha_limite = fecha_denuncia + datetime.timedelta(days=int(limites)*30)
            dias_restantes = (fecha_limite - datetime.date.today()).days
            dias_sentencia = f"{dias_restantes} días (plazo máximo: {limites} meses desde la denuncia)"
        else:
            dias_sentencia = 'No disponible'
        # Cartilla resumen
        st.markdown(f"""
        <div class="cardilla">
        <h3>📋 Resumen de la denuncia</h3>
        <ul>
            <li><strong>Fecha de denuncia:</strong> {fecha_denuncia}</li>
            <li><strong>Ciudad:</strong> {ciudad}</li>
            <li><strong>Localidad:</strong> {localidad}</li>
            <li><strong>Cantidad de agresores:</strong> {cantidad_agresores}</li>
            <li><strong>Tipo de arma usada:</strong> {tipo_arma}</li>
            <li><strong>Asistencia policial:</strong> {asistencia_policial}</li>
            <li><strong>Delitos presentes:</strong> {', '.join(delitos_seleccionados)}</li>
            <li><strong>Descripción:</strong> {descripcion}</li>
        </ul>
        <h4>🔎 Análisis judicial</h4>
        <ul>
            <li><strong>Tiempo estimado de condena por delito:</strong><br> {'<br>'.join(condenas)}</li>
            <li><strong>Plazo para dictar sentencia:</strong> {dias_sentencia}</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        # Función para conectar con Gemini y obtener análisis
        def analizar_con_gemini(api_key, denuncia):
            modelo = 'gemini-pro'  # Cambia si tu API muestra otro modelo disponible
            url = f'https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent'
            headers = {'Content-Type': 'application/json'}
            payload = {
                'contents': [{'parts': [{'text': denuncia}]}],
                'generationConfig': {'temperature': 0.7}
            }
            params = {'key': api_key}
            response = requests.post(url, headers=headers, params=params, json=payload)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                return f'Error: {response.text}'

        if api_key:
            st.subheader('🧠 Análisis de Gemini para la denuncia')
            prompt = f"Analiza la siguiente denuncia judicial y proporciona un resumen, posibles recomendaciones y riesgos legales:\n{descripcion}"
            resultado_gemini = analizar_con_gemini(api_key, prompt)
            st.write(resultado_gemini)
        else:
            st.info('Ingrese su clave API para obtener el análisis de Gemini.')

        # Guardar denuncia en archivo CSV
        def guardar_denuncia(data):
            file_exists = os.path.isfile(DENUNCIAS_PATH)
            with open(DENUNCIAS_PATH, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['fecha_denuncia','ciudad','localidad','cantidad_agresores','asistencia_policial','delitos','tipo_arma','descripcion'])
                writer.writerow(data)

        guardar_denuncia([
            fecha_denuncia,
            ciudad,
            localidad,
            cantidad_agresores,
            asistencia_policial,
            ', '.join(delitos_seleccionados),
            tipo_arma,
            descripcion
        ])
        st.success('Denuncia registrada y guardada correctamente.')

# Mueve la definición de cargar_denuncias arriba para que esté disponible antes de su uso
def cargar_denuncias():
    if not os.path.isfile(DENUNCIAS_PATH):
        return []
    with open(DENUNCIAS_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

# Opción para consultar el repositorio de denuncias
st.sidebar.subheader('📁 Consultar denuncias registradas')
if st.sidebar.button('Ver denuncias'):
    denuncias = cargar_denuncias()
    if denuncias:
        st.subheader('📋 Repositorio de denuncias registradas')
        st.dataframe(denuncias)
    else:
        st.info('No hay denuncias registradas aún.')
