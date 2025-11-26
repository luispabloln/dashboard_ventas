import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os
from io import StringIO

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Master Sales Command v22.1", page_icon="💎", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F4F6F9; color: #2C3E50; }
    .metric-card { background-color: #FFFFFF; border-radius: 12px; padding: 15px; border: 1px solid #E5E8EB; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
    .alert-box { padding: 15px; border-radius: 8px; margin-bottom: 15px; font-weight: 500; }
    .alert-danger { background-color: #FDEDEC; border-left: 5px solid #E74C3C; color: #C0392B; }
    .alert-warning { background-color: #FFF3CD; border-left: 5px solid #FFC107; color: #856404; }
    .alert-success { background-color: #EAFAF1; border-left: 5px solid #2ECC71; color: #27AE60; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN DE LECTURA DE ARCHIVOS CONSOLIDADOS DESDE REPOSITORIO ---
@st.cache_data
def load_consolidated_data():
    
    # LISTA DE POSIBLES NOMBRES EN EL REPOSITORIO
    VENTA_FILES = ['venta_completa.csv', 'Venta_Completa.csv']
    PREVENTA_FILES = ['preventa_completa.csv', 'PREVENTA AL 22 DE NOBIEMBRE.xlsx - PreVentasProveedor.csv']
    MAESTRO_FILES = ['maestro_de_clientes.csv', 'Maestro_de_clientes.csv', 'Maestro_de_Clientes.csv', 'asignaciones.csv'] 
    
    df_v, df_p, df_a = None, None, None
    
    def read_and_clean(file_path):
        try:
            df_temp = pd.read_csv(file_path, sep=';', on_bad_lines='skip', encoding='utf-8')
            if df_temp.shape[1] < 5: 
                df_temp = pd.read_csv(file_path, sep=',', on_bad_lines='skip', encoding='utf-8')
            
            df_temp.columns = df_temp.columns.str.strip().str.lower().str.replace(' ', '_')
            return df_temp
        except Exception:
            return None

    # LECTURA DE VENTA
    for name in VENTA_FILES:
        if os.path.exists(name):
            df_v_raw = read_and_clean(name)
            if df_v_raw is not None and 'fecha' in df_v_raw.columns:
                df_v = df_v_raw
                # ... (resto de la limpieza de df_v) ...
                df_v['clienteid'] = df_v['clienteid'].astype(str)
                df_v['cliente'] = df_v['cliente'].astype(str).str.strip().str.upper()
                df_v['fecha'] = pd.to_datetime(df_v['fecha'], format='%d/%m/%Y', dayfirst=True, errors='coerce')
                df_v['semana_anio'] = df_v['fecha'].dt.isocalendar().week
                df_v['monto_real'] = df_v.get('montofinal', df_v['monto'])
                df_v['id_transaccion'] = df_v.get('ventaid', df_v.columns[0])
                df_v['canal'] = df_v['vendedor'].map({'JOSE CARLOS MENDOZA MENDOZA': '1. MAYORISTAS', 'KEVIN  COLODRO VACA': '1. MAYORISTAS', 'MARCIA MARAZ MONTAÑO': '1. MAYORISTAS', 'ABDY JOSE RUUD': '1. MAYORISTAS', 'MARIBEL ROLLANO CHOQUE': '2. PERIFERIA', 'RAFAEL SARDAN SALAZAR': '3. FARMACIAS', 'LUIS PABLO LOPEZ NEGRETE': '4. INSTITUCIONAL', 'JAVIER JUSTINIANO GOMEZ': '5. PARETOS TDB'}).fillna('6. RUTA TDB')
                break

    # LECTURA DE ASIGNACIONES (MAESTRO DE CLIENTES - FIX CRÍTICO DE BÚSQUEDA)
    for name in MAESTRO_FILES:
        if os.path.exists(name):
            df_a_raw = read_and_clean(name)
            if df_a_raw is not None and 'cliente_id' in df_a_raw.columns and 'vendedor' in df_a_raw.columns:
                df_a = df_a_raw.copy()
                df_a = df_a.rename(columns={'cliente_id': 'clienteid'}) # UNIFICAR LLAVE
                df_a['clienteid'] = df_a['clienteid'].astype(str)
                df_a['vendedor'] = df_a['vendedor'].astype(str).str.strip()
                df_a = df_a[['clienteid', 'vendedor']].drop_duplicates(subset=['clienteid']) 
                break # Sale del loop si encuentra el archivo

    # LECTURA DE PREVENTA (omisión para brevedad)
    for name in PREVENTA_FILES:
        if os.path.exists(name):
            df_p_raw = read_and_clean(name)
            if df_p_raw is not None and 'fecha' in df_p_raw.columns:
                df_p = df_p_raw
                df_p['fecha'] = pd.to_datetime(df_p['fecha'], format='%d/%m
