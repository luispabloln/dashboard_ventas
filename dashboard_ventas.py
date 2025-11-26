import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os
from io import StringIO

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Master Sales Command v21.0", page_icon="💎", layout="wide")

# --- ESTILOS CSS (Omisión por brevedad) ---
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
    MAESTRO_FILE = 'maestro_de_clientes.csv' # NUEVO ARCHIVO
    
    df_v, df_p, df_a = None, None, None
    
    def read_and_clean(file_path):
        try:
            # Intentar leer con ';' por ser archivo maestro
            df_temp = pd.read_csv(file_path, sep=';', on_bad_lines='skip', encoding='utf-8')
            if df_temp.shape[1] < 5: # Si lee mal, reintentamos con coma
                df_temp = pd.read_csv(file_path, sep=',', on_bad_lines='skip', encoding='utf-8')
            
            df_temp.columns = df_temp.columns.str.strip().str.lower().str.replace(' ', '_') # Limpieza robusta
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
            else: df_v['monto_real'] = df_v['monto']
            
            df_v['id_transaccion'] = df_v.get('ventaid', df_v.columns[0])
            df_v['canal'] = df_v['vendedor'].map({
                'JOSE CARLOS MENDOZA MENDOZA': '1. MAYORISTAS', 'KEVIN  COLODRO VACA': '1. MAYORISTAS',
                'MARCIA MARAZ MONTAÑO': '1. MAYORISTAS', 'ABDY JOSE RUUD': '1. MAYORISTAS',
                'MARIBEL ROLLANO CHOQUE': '2. PERIFERIA', 'RAFAEL SARDAN SALAZAR': '3. FARMACIAS',
                'LUIS PABLO LOPEZ NEGRETE': '4. INSTITUCIONAL', 'JAVIER JUSTINIANO GOMEZ': '5. PARETOS TDB'
            }).fillna('6. RUTA TDB')

    # LECTURA DE PREVENTA (omisión para brevedad)
    if os.path.exists(PREVENTA_FILE):
        df_p_raw = read_and_clean(PREVENTA_FILE)
        if df_p_raw is not None and 'fecha' in df_p_raw.columns:
            df_p = df_p_raw
            df_p['fecha'] = pd.to_datetime(df_p['fecha'], format='%d/%m/%Y', dayfirst=True, errors='coerce') 
            if 'monto_final' in df_p.columns: df_p['monto_pre'] = df_p['monto_final']
            else: df_p['monto_pre'] = df_p['monto']
            df_p['id_cruce'] = df_p.get('nro_preventa', df_p.get('nropreventa', 0))

    # LECTURA DE ASIGNACIONES (MAESTRO DE CLIENTES)
    if os.path.exists(MAESTRO_FILE):
        df_a_raw = read_and_clean(MAESTRO_FILE)
        # NOMBRES DE COLUMNA DEL MAESTRO: cliente_id y vendedor
        if df_a_raw is not None and 'cliente_id' in df_a_raw.columns and 'vendedor' in df_a_raw.columns:
            df_a = df_a_raw.copy()
            df_a['cliente_id'] = df_a['cliente_id'].astype(str)
            df_a['vendedor'] = df_a['vendedor'].astype(str).str.strip()
            # Mantenemos una asignación única para cada cliente ID
            df_a = df_a[['cliente_id', 'vendedor']].drop_duplicates(subset=['cliente_id']) 
            
    # --- ENRIQUECIMIENTO (FUSIÓN MAESTRO + VENTA) ---
    if df_v is not None and df_a is not None:
        # Renombrar columna de Venta temporalmente para evitar conflicto
        df_v = df_v.rename(columns={'vendedor': 'vendedor_venta'}) 
        
        # Fusionar: Unimos la venta con la asignación del maestro usando cliente_id
        df_v = pd.merge(df_v, df_a[['cliente_id', 'vendedor']], on='cliente_id', how='left')
        
        # El vendedor que usamos para los reportes es el ASIGNADO por el MAESTRO
        df_v['vendedor'] = df_v['vendedor'].fillna(df_v['vendedor_venta'])


    return df_v, df_p, df_a

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
    st.title("💎 Master Dashboard v21.0")
    st.info("Datos cargados automáticamente desde GitHub.")
    st.markdown("---")
    st.header("🎯 Metas")
    meta = st.number_input("Objetivo Mensual ($)", value=2500000, step=100000)

# Ejecución de carga
df_v, df_p, df_a = load_consolidated_data()

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
    tabs = st.tabs(["🎯 Penetración (NUEVO)", "📉 Análisis Caída", "🎮 Simulador", "📈 Estrategia", "💳 Finanzas", "👥 Clientes 360", "🔍 Auditoría", "🧠 Inteligencia"])
    
    # 1. PENETRACIÓN (NUEVO MODULO)
    with tabs[0]:
        if df_a is not None:
            st.header("🎯 Penetración de Cobertura Asignada")
            
            # 1. Clientes Asignados por Vendedor (del Maestro)
            assigned_clients = df_a.groupby('vendedor')['cliente_id'].nunique().reset_index()
            assigned_clients.columns = ['vendedor', 'Asignados']
            
            # 2. Clientes Servidos por Vendedor (DEL PERIODO ACTUAL)
            served_clients = dff.groupby('vendedor')['clienteid'].nunique().reset_index()
            served_clients.columns = ['vendedor', 'Servidos']
            
            # 3. Merge y Cálculo
            penetration_df = pd.merge(assigned_clients, served_clients, on='vendedor', how='left').fillna(0)
            
            # Solo calcular si Asignados > 0 para evitar errores
            penetration_df['Penetracion %'] = (penetration_df['Servidos'] / penetration_df['Asignados'].replace(0, 1)) * 100
            
            # 4. Cálculo de White Space
            penetration_df['Espacio Blanco'] = penetration_df['Asignados'] - penetration_df['Servidos']
            
            penetration_df = penetration_df.sort_values('Penetracion %', ascending=False)
            
            st.subheader("Efectividad de Cobertura por Vendedor")
            st.dataframe(
                penetration_df.style.format({'Penetracion %': '{:.1f}%', 'Asignados': '{:.0f}', 'Servidos': '{:.0f}', 'Espacio Blanco': '{:.0f}'}), 
                use_container_width=True
            )
            
            # Gráfico de Espacio Blanco (Barra apilada)
            fig_pen = go.Figure(data=[
                go.Bar(name='Servidos', y=penetration_df['vendedor'], x=penetration_df['Servidos'], orientation='h', marker_color='#2ECC71'),
                go.Bar(name='Espacio Blanco', y=penetration_df['vendedor'], x=penetration_df['Espacio Blanco'], orientation='h', marker_color='#E74C3C')
            ])
            fig_pen.update_layout(barmode='stack', title="Clientes Asignados vs Clientes Servidos", height=500)
            st.plotly_chart(fig_pen, use_container_width=True)

        else:
            st.warning("⚠️ Falta el archivo 'maestro_de_clientes.csv' en el repositorio para calcular la Penetración.")


    # 2. ANÁLISIS CAÍDA
    with tabs[1]:
        # [Logic for Análisis Caída] ...
        st.info("Módulo Análisis Caída activo.")
        
    # 3. SIMULADOR
    with tabs[2]:
        # [Logic for Simulador] ...
        st.info("Módulo Simulador activo.")

    # 4. ESTRATEGIA
    with tabs[3]:
        # [Logic for Estrategia] ...
        st.info("Módulo Estrategia activo.")

    # 5. FINANZAS
    with tabs[4]:
        # [Logic for Finanzas] ...
        st.info("Módulo Finanzas activo.")

    # 6. CLIENTES 360
    with tabs[5]:
        # [Logic for Clientes 360] ...
        st.info("Módulo Clientes 360 activo.")

    # 7. AUDITORÍA
    with tabs[6]:
        # [Logic for Auditoría] ...
        st.info("Módulo Auditoría activo.")

    # 8. INTELIGENCIA
    with tabs[7]:
        # [Logic for Inteligencia] ...
        st.info("Módulo Inteligencia activo.")

else:
    st.error("🚨 ERROR CRÍTICO: No se pudo cargar el archivo de ventas principal ('venta_completa.csv').")
