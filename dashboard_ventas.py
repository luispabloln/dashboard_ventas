import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os
from io import StringIO

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Master Sales Command v18.0", page_icon="💎", layout="wide")

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
    VENTA_FILE = 'venta_completa.csv'
    PREVENTA_FILE = 'preventa_completa.csv'
    
    df_v, df_p = None, None
    
    def read_and_clean(file_path):
        try:
            df_temp = pd.read_csv(file_path, sep=',', on_bad_lines='skip', encoding='utf-8')
            if df_temp.shape[1] < 5: 
                df_temp = pd.read_csv(file_path, sep=';', on_bad_lines='skip', encoding='utf-8')
            
            df_temp.columns = df_temp.columns.str.strip().str.lower()
            return df_temp
        except Exception:
            return None

    # LECTURA DE VENTA
    if os.path.exists(VENTA_FILE):
        df_v_raw = read_and_clean(VENTA_FILE)
        if df_v_raw is not None and 'fecha' in df_v_raw.columns:
            df_v = df_v_raw
            df_v['fecha'] = pd.to_datetime(df_v['fecha'], format='%d/%m/%Y', dayfirst=True, errors='coerce')
            df_v['semana_anio'] = df_v['fecha'].dt.isocalendar().week
            
            if 'montofinal' in df_v.columns: df_v['monto_real'] = df_v['montofinal']
            elif 'monto' in df_v.columns: df_v['monto_real'] = df_v['monto']
            else: df_v['monto_real'] = 0
            
            df_v['id_transaccion'] = df_v.get('ventaid', df_v.columns[0])
            df_v['canal'] = df_v['vendedor'].map({
                'JOSE CARLOS MENDOZA MENDOZA': '1. MAYORISTAS', 'KEVIN  COLODRO VACA': '1. MAYORISTAS',
                'MARCIA MARAZ MONTAÑO': '1. MAYORISTAS', 'ABDY JOSE RUUD': '1. MAYORISTAS',
                'MARIBEL ROLLANO CHOQUE': '2. PERIFERIA', 'RAFAEL SARDAN SALAZAR': '3. FARMACIAS',
                'LUIS PABLO LOPEZ NEGRETE': '4. INSTITUCIONAL', 'JAVIER JUSTINIANO GOMEZ': '5. PARETOS TDB'
            }).fillna('6. RUTA TDB')

    # LECTURA DE PREVENTA
    if os.path.exists(PREVENTA_FILE):
        df_p_raw = read_and_clean(PREVENTA_FILE)
        if df_p_raw is not None and 'fecha' in df_p_raw.columns:
            df_p = df_p_raw
            if 'monto final' in df_p.columns: df_p['monto_pre'] = df_p['monto final']
            elif 'monto' in df_p.columns: df_p['monto_pre'] = df_p['monto']
            else: df_p['monto_pre'] = 0
            df_p['id_cruce'] = df_p.get('nro preventa', df_p.get('nropreventa', 0))
            
    return df_v, df_p

# --- FUNCIÓN PARA OBTENER FECHA MÁXIMA DE FORMA SEGURA ---
def get_max_date_safe(df):
    if df is not None and not df.empty and 'fecha' in df.columns:
        valid_dates = df['fecha'].dropna()
        if not valid_dates.empty:
            try:
                return valid_dates.max().strftime('%d-%m-%Y')
            except AttributeError:
                return "Corrupción Grave"
    return "No disponible"


# --- INTERFAZ ---
with st.sidebar:
    st.title("💎 Master Dashboard v18.0")
    st.info("Datos cargados automáticamente desde GitHub.")
    st.markdown("---")
    st.header("🎯 Metas")
    meta = st.number_input("Objetivo Mensual ($)", value=2500000, step=100000)

# Ejecución de carga
df_v, df_p = load_consolidated_data()

if df_v is not None:
    
    # --- FILTRO Y PREPARACIÓN DE DATOS ---
    sel_canal = st.multiselect("Filtro Canal", df_v['canal'].unique(), default=df_v['canal'].unique())
    dff = df_v[df_v['canal'].isin(sel_canal)].copy()
    
    # KPIs Globales
    tot = dff['monto_real'].sum()
    cobertura = dff['cliente'].nunique()
    trx = dff['id_transaccion'].nunique()
    ticket = tot / trx if trx > 0 else 0

    # HEADER
    c1, c2 = st.columns([1, 2])
    with c1:
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = tot,
            title = {'text': "Progreso Meta", 'font': {'size': 14}},
            delta = {'reference': meta, 'increasing': {'color': "green"}},
            gauge = {'axis': {'range': [None, meta*1.2]}, 'bar': {'color': "#2C3E50"}, 'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': meta}}))
        st.plotly_chart(fig_gauge, use_container_width=True)
    with c2:
        k1, k2, k3 = st.columns(3)
        k1.metric("Ventas Totales", f"${tot:,.0f}")
        k2.metric("Cobertura", f"{cobertura} Clientes")
        k3.metric("Ticket Promedio", f"${ticket:,.0f}")
        
        if df_p is not None:
            tot_pre = df_p['monto_pre'].sum()
            caida = tot_pre - tot
            pct_caida = (caida / tot_pre) * 100 if tot_pre > 0 else 0
            st.markdown(f'<div class="alert-box alert-warning">📉 <b>FILL RATE:</b> Rechazo de ${caida:,.0f} ({pct_caida:.1f}% de preventa).</div>', unsafe_allow_html=True)

    st.markdown("---")
    
    # --- REPORTE DE SINCRONIZACIÓN ---
    st.subheader("✅ Estado de Sincronización de Datos")
    max_v_date = get_max_date_safe(df_v)
    max_p_date = get_max_date_safe(df_p)
    if max_v_date != "No disponible" and max_p_date != "No disponible" and max_v_date == max_p_date:
        sync_message = f'
