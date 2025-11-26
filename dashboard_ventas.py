import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os
from io import StringIO

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Master Sales Command v20.0", page_icon="💎", layout="wide")

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
            
            if 'clienteid' in df_v.columns: df_v['clienteid'] = df_v['clienteid'].astype(str)
            if 'cliente' in df_v.columns: df_v['cliente'] = df_v['cliente'].astype(str).str.strip().str.upper()

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
            df_p['fecha'] = pd.to_datetime(df_p['fecha'], format='%d/%m/%Y', dayfirst=True, errors='coerce') 

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
    st.title("💎 Master Dashboard v20.0")
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
    cobertura = dff['clienteid'].nunique()
    trx = dff['id_transaccion'].nunique()
    ticket = tot / trx if trx > 0 else 0

    # HEADER
    c1, c2 = st.columns([1, 2])
    with c1:
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta", value = tot,
            title = {'text': "Progreso Meta", 'font': {'size': 14}},
            delta = {'reference': meta, 'increasing': {'color': "green"}},
            gauge = {'axis': {'range': [None, meta*1.2]}, 'bar': {'color': "#2C3E50"}, 'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': meta}}))
        fig_gauge.update_layout(height=200, margin=dict(t=30,b=10,l=30,r=30))
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
        sync_message = f'<div class="alert-box alert-success">🟢 **Sincronización PERFECTA:** Ambas bases están al día hasta el **{max_v_date}**.</div>'
    elif max_v_date != "No disponible" or max_p_date != "No disponible":
        sync_message = f'<div class="alert-box alert-warning">🟡 **Advertencia:** Venta (Final) al **{max_v_date}** vs. Preventa (Pedido) al **{max_p_date}**. Revise la Preventa.</div>'
    else:
        sync_message = '<div class="alert-box alert-danger">🔴 **ERROR CRÍTICO:** No se pudo cargar ninguna fecha válida. Revise los archivos.</div>'

    st.markdown(sync_message, unsafe_allow_html=True)
    st.markdown("---")


    # --- PESTAÑAS (TODAS FUNCIONALES) ---
    tabs = st.tabs(["📉 Análisis Caída", "🎮 Simulador", "📈 Estrategia", "💳 Finanzas", "👥 Clientes 360", "🔍 Auditoría", "🧠 Inteligencia"])
    
    # 1. ANÁLISIS CAÍDA (Omitido para la corrección)

    # 2. SIMULADOR (Omitido para la corrección)

    # 3. ESTRATEGIA (Combo Chart y Sunburst)
    with tabs[2]:
        st.header("📈 Estrategia y Visión Macro")
        if not dff.empty and 'clienteid' in dff.columns:
            
            # --- COMBO CHART (TENDENCIA) ---
            st.subheader("Venta vs Penetración (Combo Chart)")
            daily = dff.groupby('fecha').agg({'monto_real':'sum', 'clienteid':'nunique'}).reset_index()
            fig_combo = go.Figure()
            fig_combo.add_trace(go.Bar(x=daily['fecha'], y=daily['monto_real'], name='Venta ($)', marker_color='#95A5A6', opacity=0.6))
            fig_combo.add_trace(go.Scatter(x=daily['fecha'], y=daily['clienteid'], name='Cobertura (Clientes)', yaxis='y2', line=dict(color='#3498DB', width=3), mode='lines+markers'))
            
            fig_combo.update_layout(yaxis=dict(title="Venta ($)", showgrid=False), yaxis2=dict(title="Cobertura (Clientes)", overlaying='y', side='right', showgrid=False), plot_bgcolor='white', height=700, title="Evolución Venta vs Clientes Únicos")
            st.plotly_chart(fig_combo, use_container_width=True)
            
            st.markdown("---")
            
            # --- SUNBURST (JERARQUÍA ABAJO) ---
            st.subheader("Jerarquía de Ventas (Sunburst)")
            sun_df = dff.groupby(['canal', 'vendedor'])['monto_real'].sum().reset_index()
            fig_sun = px.sunburst(sun_df, path=['canal', 'vendedor'], values='monto_real', color='monto_real', color_continuous_scale='Blues')
            fig_sun.update_layout(height=600, margin=dict(t=0, l=0, r=0, b=0))
            st.plotly_chart(fig_sun, use_container_width=True)
            
        else: st.warning("No hay datos para esta vista.")

    # 4. FINANZAS (omitted for brevity)

    # 5. CLIENTES (omitted for brevity)
    
    # 6. AUDITORÍA (FIX DE FILTROS AQUI)
    with tabs[5]:
        st.header("🕵️ Mapa de Oportunidades (Gaps)")
        if not dff.empty:
            
            # --- 1. CONFIGURACIÓN DE FILTROS DE PRODUCTO ---
            st.subheader("Filtros de Análisis")
            
            # Opciones de jerarquía (Quitamos NaN para los multiselect)
            j1_opts = sorted(dff['jerarquia1'].dropna().unique()) if 'jerarquia1' in dff.columns else []
            j2_opts = sorted(dff['jerarquia2'].dropna().unique()) if 'jerarquia2' in dff.columns else []
            cat_opts = sorted(dff['categoria'].dropna().unique()) if 'categoria' in dff.columns else []
            prod_opts = sorted(dff['producto'].dropna().unique()) if 'producto' in dff.columns else []

            # UI Layout para filtros (2 columnas)
            col_f1, col_f2 = st.columns(2)
            
            with col_f1:
                sel_j1 = st.multiselect("Filtro por Jerarquía 1", options=j1_opts)
                sel_cat = st.multiselect("Filtro por Categoría", options=cat_opts)
            
            with col_f2:
                sel_j2 = st.multiselect("Filtro por Jerarquía 2", options=j2_opts)
                sel_prod = st.multiselect("Filtro por Producto", options=prod_opts)

            # --- 2. APLICACIÓN DE FILTROS Y LÓGICA DE AGRUPACIÓN ---
            df_audit = dff.copy()

            # Aplicar filtros secuencialmente
            if sel_j1: df_audit = df_audit[df_audit['jerarquia1'].isin(sel_j1)]
            if sel_j2: df_audit = df_audit[df_audit['jerarquia2'].isin(sel_j2)]
            if sel_cat: df_audit = df_audit[df_audit['categoria'].isin(sel_cat)]
            if sel_prod: df_audit = df_audit[df_audit['producto'].isin(sel_prod)]

            
            if not df_audit.empty:
                # Determinar la columna de agrupación más granular
                if sel_prod:
                    col_group = 'producto'
                elif sel_cat:
                    col_group = 'categoria'
                elif sel_j2:
                    col_group = 'jerarquia2'
                elif sel_j1:
                    col_group = 'jerarquia1'
                else:
                    col_group = 'jerarquia1' # Default si no hay filtros aplicados
                
                # --- 3. HEATMAP CALCULATION ---
                st.subheader(f"Mapa de Calor: Vendedor vs {col_group.upper()}")
                
                pivot = df_audit.groupby(['vendedor', col_group])['monto_real'].sum().reset_index().pivot(index='vendedor', columns=col_group, values='monto_real').fillna(0)
                
                fig_heat = px.imshow(pivot, text_auto='.2s', aspect="auto", color_continuous_scale='Blues', title=f"Venta por {col_group.upper()}")
                st.plotly_chart(fig_heat, use_container_width=True)
                
            else:
                st.warning("No hay datos que coincidan con los filtros seleccionados.")
        else:
            st.warning("No hay datos para esta vista.")

    # 7. INTELIGENCIA (omitted for brevity)

else:
    # 🚨 ERROR SI NO ENCUENTRA EL ARCHIVO PRINCIPAL
    st.error("🚨 ERROR CRÍTICO: No se pudo cargar el archivo de ventas principal ('venta_completa.csv').")
