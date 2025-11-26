import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os
from io import StringIO

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Master Sales Command v17", page_icon="💎", layout="wide")

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
    
    # Lista de nombres de archivos consolidados que deben existir en el repositorio
    VENTA_FILE = 'venta_completa.csv'
    PREVENTA_FILE = 'preventa_completa.csv'
    
    df_v, df_p = None, None
    
    # Función de lectura y limpieza interna
    def read_and_clean(file_path):
        try:
            # 1. Leer archivo (intentar como CSV con ; y después como CSV con ,)
            df_temp = pd.read_csv(file_path, sep=';', on_bad_lines='skip', encoding='utf-8')
            if df_temp.shape[1] < 5: # Si lee menos de 5 columnas, reintentamos con coma
                df_temp = pd.read_csv(file_path, sep=',', on_bad_lines='skip', encoding='utf-8')
            
            # 2. Limpieza de columnas
            df_temp.columns = df_temp.columns.str.strip().str.lower()
            
            return df_temp
        except Exception as e:
            st.error(f"Error al leer el archivo {file_path}. Asegúrate de que existe y es CSV válido. Error: {e}")
            return None

    # LECTURA DE VENTA
    if os.path.exists(VENTA_FILE):
        df_v_raw = read_and_clean(VENTA_FILE)
        if df_v_raw is not None and 'fecha' in df_v_raw.columns:
            df_v = df_v_raw
            df_v['fecha'] = pd.to_datetime(df_v['fecha'], format='%d/%m/%Y', dayfirst=True, errors='coerce')
            df_v = df_v.sort_values('fecha')
            df_v['semana_anio'] = df_v['fecha'].dt.isocalendar().week
            
            if 'montofinal' in df_v.columns: df_v['monto_real'] = df_v['montofinal']
            elif 'monto' in df_v.columns: df_v['monto_real'] = df_v['monto']
            else: df_v['monto_real'] = 0
            
            col_id = 'ventaid' if 'ventaid' in df_v.columns else 'venta' # Fallback
            df_v['id_transaccion'] = df_v[col_id]
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
            
            if 'nro preventa' in df_p.columns: df_p['id_cruce'] = df_p['nro preventa']
            elif 'nropreventa' in df_p.columns: df_p['id_cruce'] = df_p['nropreventa']
            else: df_p['id_cruce'] = 0


    return df_v, df_p


# --- INTERFAZ ---
with st.sidebar:
    st.title("💎 Master Dashboard v17")
    st.success("Archivos cargados automáticamente desde el repositorio.")
    st.markdown("---")
    st.header("🎯 Metas")
    meta = st.number_input("Objetivo Mensual ($)", value=2500000, step=100000)


# Ejecución de carga (SIN EL ARCHIVO UPLOADER)
df_v, df_p = load_consolidated_data()

if df_v is not None:
    # FILTROS Y PROCESAMIENTO
    sel_canal = st.multiselect("Filtro Canal", df_v['canal'].unique(), default=df_v['canal'].unique())
    dff = df_v[df_v['canal'].isin(sel_canal)]
    
    tot = dff['monto_real'].sum()
    cobertura = dff['cliente'].nunique()
    trx = dff['id_transaccion'].nunique()
    ticket = tot/trx if trx>0 else 0
    
    # SECCIÓN SUPERIOR
    c1, c2 = st.columns([1, 2])
    with c1:
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta", value = tot,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Progreso Meta", 'font': {'size': 14}},
            delta = {'reference': meta, 'increasing': {'color': "green"}},
            gauge = {'axis': {'range': [None, meta*1.2]}, 'bar': {'color': "#2C3E50"}, 'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': meta}}))
        fig_gauge.update_layout(height=200, margin=dict(t=30,b=10,l=30,r=30))
        st.plotly_chart(fig_gauge, use_container_width=True)
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
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

    # --- PESTAÑAS ---
    tabs = st.tabs(["📉 Análisis Caída", "🎮 Simulador", "📈 Estrategia", "💳 Finanzas", "👥 Clientes 360", "🔍 Auditoría", "🧠 Inteligencia"])
    
    # 1. ANÁLISIS CAÍDA
    with tabs[0]:
        if df_p is not None and 'id_cruce' in df_p.columns:
            st.header("📉 Análisis de Eficiencia Logística")
            
            ven_g = dff.groupby('preventaid')['monto_real'].sum().reset_index()
            pre_g = df_p.groupby('id_cruce')['monto_pre'].sum().reset_index()
            merge_detail = pd.merge(df_p, ven_g, left_on='id_cruce', right_on='preventaid', how='left').fillna(0)
            merge_detail['caida_val'] = merge_detail['monto_pre'] - merge_detail['monto_real']
            
            c_f1, c_f2 = st.columns(2)
            
            with c_f1:
                # Top Vendedores con Caida (Factor de Riesgo)
                v_agg = merge_detail.groupby('vendedor').agg(
                    total_pre=('monto_pre', 'sum'),
                    total_caida=('caida_val', 'sum')
                ).reset_index()
                v_agg['% Caída'] = (v_agg['total_caida'] / v_agg['total_pre']) * 100
                drop_vend = v_agg.sort_values(by='% Caída', ascending=False).head(10)
                st.plotly_chart(px.bar(drop_vend, x='% Caída', y='vendedor', orientation='h', title="Vendedores con Mayor % de Pedidos Caídos", color_continuous_scale='Reds'), use_container_width=True)
            
            with c_f2:
                # Productos No Entregados (Quiebres de Stock)
                prod_drop = merge_detail.groupby('producto')['caida_val'].sum().sort_values(ascending=False).head(10).reset_index()
                st.dataframe(prod_drop.style.format({'caida_val': '${:,.2f}'}), use_container_width=True)
                
        else:
            st.warning("⚠️ Asegúrate que el archivo 'preventa_completa.csv' esté en el repositorio.")

    # 2. SIMULADOR (Continúa en el código original...)
        with tabs[1]:
            st.header("🎮 Simulador de Cierre")
            col_sim_input, col_sim_res = st.columns([1, 2])
            with col_sim_input:
                st.markdown('<div class="metric-card"><h5>🎛️ Ajustes</h5>', unsafe_allow_html=True)
                days_left = max(0, 30 - dff['fecha'].max().day)
                st.info(f"Días restantes: {days_left}")
                delta_ticket = st.slider("Subir Ticket (%)", 0, 50, 0)
                delta_clientes = st.slider("Subir Cobertura (%)", 0, 50, 0)
                st.markdown('</div>', unsafe_allow_html=True)
            with col_sim_res:
                daily_avg = tot / dff['fecha'].max().day
                proj_natural = tot + (daily_avg * days_left)
                proj_sim = tot + (daily_avg * (1+delta_ticket/100) * (1+delta_clientes/100) * days_left)
                m1, m2, m3 = st.columns(3)
                m1.metric("Cierre Natural", f"${proj_natural:,.0f}")
                m2.metric("Cierre Simulado", f"${proj_sim:,.0f}", delta=f"+${proj_sim-proj_natural:,.0f}")
                m3.metric("vs Meta", f"${proj_sim - meta:,.0f}")
            
            # Gráfico de proyección (simplificado para la respuesta)
            st.info("Gráfico de proyección de trayectoria de cierre...")


    # 3. ESTRATEGIA (Continúa en el código original...)
        with tabs[2]:
            st.header("📈 Estrategia y Visión Macro")
            st.info("Visualizaciones Sunburst y Combo Chart...")
            
    # 4. FINANZAS (Continúa en el código original...)
        with tabs[3]:
            st.header("💳 Salud Financiera")
            st.info("Análisis de Contado vs Crédito...")

    # 5. CLIENTES (Continúa en el código original...)
        with tabs[4]:
            st.header("👥 Gestión de Clientes 360")
            st.info("Buscador de cliente y Fuga...")
            
    # 6. AUDITORÍA (Continúa en el código original...)
        with tabs[5]:
            st.header("🔍 Auditoría Operativa")
            st.info("Mapa de calor de Vendedor vs Categoría...")
            
    # 7. INTELIGENCIA (Continúa en el código original...)
        with tabs[6]:
            st.header("🧠 Cross-Selling")
            st.info("Recomendador de productos...")


else:
    st.error("⚠️ Error: No se pudo cargar el archivo de ventas principal ('venta_completa.csv'). Asegúrate de que los archivos están en tu repositorio y se llaman correctamente.")
