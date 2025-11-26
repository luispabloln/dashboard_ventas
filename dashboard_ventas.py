import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os
from io import StringIO

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Master Sales Command v19.2", page_icon="💎", layout="wide")

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
    st.title("💎 Master Dashboard v19.2")
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
    
    # 1. ANÁLISIS CAÍDA
    with tabs[0]:
        if df_p is not None and not dff.empty:
            st.header("📉 Análisis de Eficiencia Logística y Comercial")
            
            ven_g = dff.groupby('preventaid')['monto_real'].sum().reset_index()
            pre_g = df_p.groupby('id_cruce')['monto_pre'].sum().reset_index()
            merge_detail = pd.merge(df_p, ven_g, left_on='id_cruce', right_on='preventaid', how='left').fillna(0)
            merge_detail['caida_val'] = merge_detail['monto_pre'] - merge_detail['monto_real']
            
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                v_agg = merge_detail.groupby('vendedor').agg(
                    total_pre=('monto_pre', 'sum'),
                    total_caida=('caida_val', 'sum')
                ).reset_index()
                v_agg['% Caída'] = (v_agg['total_caida'] / v_agg['total_pre']) * 100
                
                st.subheader("Top Vendedores con Mayor % de Pedidos Caídos")
                drop_vend = v_agg.sort_values(by='% Caída', ascending=False).head(10)
                st.dataframe(drop_vend.style.format({'total_pre': '${:,.0f}', 'total_caida': '${:,.0f}', '% Caída': '{:.1f}%'}), use_container_width=True)
            
            with c_f2:
                st.subheader("Productos No Entregados (Quiebres de Stock)")
                prod_drop = merge_detail.groupby('producto')['caida_val'].sum().sort_values(ascending=False).head(10).reset_index()
                st.dataframe(prod_drop.style.format({'caida_val': '${:,.2f}'}), use_container_width=True)
        else:
            st.warning("Carga el archivo 'preventa_completa.csv' y asegúrate de que el filtro no esté vacío.")

    # 2. SIMULADOR
    with tabs[1]:
        st.header("🎮 Simulador de Cierre")
        if not dff.empty:
            col_sim_input, col_sim_res = st.columns([1, 2])
            with col_sim_input:
                st.markdown('<div class="metric-card"><h5>🎛️ Ajustes</h5>', unsafe_allow_html=True)
                days_left = max(0, 30 - dff['fecha'].max().day)
                st.info(f"Días restantes: {days_left}")
                delta_ticket = st.slider("Subir Ticket (%)", 0, 50, 0)
                delta_clientes = st.slider("Subir Cobertura (%)", 0, 50, 0)
                st.markdown('</div>', unsafe_allow_html=True)
            with col_sim_res:
                days_available = dff['fecha'].nunique()
                daily_avg = tot / days_available if days_available > 0 else 0
                proj_natural = tot + (daily_avg * days_left)
                proj_sim = tot + (daily_avg * (1+delta_ticket/100) * (1+delta_clientes/100) * days_left)
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Cierre Natural", f"${proj_natural:,.0f}")
                m2.metric("Cierre Simulado", f"${proj_sim:,.0f}", delta=f"+${proj_sim-proj_natural:,.0f}")
                m3.metric("vs Meta", f"${proj_sim - meta:,.0f}")
        else:
            st.warning("No hay datos para simular.")

    # 3. ESTRATEGIA (CON COMBO CHART CORREGIDO)
    with tabs[2]:
        st.header("📈 Estrategia y Visión Macro")
        if not dff.empty and 'clienteid' in dff.columns:
            c_m1, c_m2 = st.columns([2, 1])
            with c_m1:
                st.subheader("Venta vs Penetración (Combo Chart)")
                
                daily = dff.groupby('fecha').agg({
                    'monto_real':'sum',
                    'clienteid':'nunique'
                }).reset_index()
                
                fig_combo = go.Figure()
                fig_combo.add_trace(go.Bar(x=daily['fecha'], y=daily['monto_real'], name='Venta ($)', marker_color='#95A5A6', opacity=0.6))
                
                fig_combo.add_trace(go.Scatter(
                    x=daily['fecha'], 
                    y=daily['clienteid'],
                    name='Cobertura (Clientes)', 
                    yaxis='y2', 
                    line=dict(color='#3498DB', width=3),
                    mode='lines+markers'
                ))
                
                fig_combo.update_layout(
                    yaxis=dict(title="Venta ($)", showgrid=False),
                    yaxis2=dict(title="Cobertura (Clientes)", overlaying='y', side='right', showgrid=False),
                    plot_bgcolor='white', height=550, title="Evolución Venta vs Clientes Únicos" # Altura ajustada
                )
                st.plotly_chart(fig_combo, use_container_width=True)
            with c_m2:
                st.subheader("Jerarquía (Sunburst)")
                sun_df = dff.groupby(['canal', 'vendedor'])['monto_real'].sum().reset_index()
                st.plotly_chart(px.sunburst(sun_df, path=['canal', 'vendedor'], values='monto_real', color='monto_real', color_continuous_scale='Blues'), use_container_width=True)
        else: st.warning("No hay datos para esta vista.")

    # 4. FINANZAS
    with tabs[3]:
        st.header("💳 Salud Financiera")
        if not dff.empty:
            pay = dff.groupby('tipopago')['monto_real'].sum().reset_index()
            cp1, cp2 = st.columns(2)
            with cp1: st.plotly_chart(px.pie(pay, values='monto_real', names='tipopago', title="Mix Cobranza"), use_container_width=True)
            with cp2:
                st.write("Ranking Crédito")
                cred_df = dff[dff['tipopago'].str.contains('Crédito', case=False, na=False)]
                if not cred_df.empty:
                    cred_rank = cred_df.groupby('vendedor')['monto_real'].sum().sort_values(ascending=False).head(10).reset_index()
                    cred_rank.columns = ['vendedor', 'monto_real'] # Asegurar nombres para el formato
                    st.dataframe(cred_rank.style.format({'monto_real': '${:,.0f}'}), use_container_width=True)
                else: st.info("No hay ventas a crédito en este filtro.")
        else: st.warning("No hay datos para esta vista.")

    # 5. CLIENTES
    with tabs[4]:
        st.header("👥 Gestión de Clientes 360°")
        if not dff.empty:
            cc1, cc2 = st.columns([1, 2])
            with cc1:
                st.markdown("#### 🔎 Buscador Individual")
                if 'cliente' in dff.columns and 'clienteid' in dff.columns and not dff['cliente'].empty:
                    
                    client_map_df = dff[['clienteid', 'cliente']].drop_duplicates()
                    client_map = client_map_df.set_index('cliente')['clienteid'].to_dict()
                    cl_list = sorted(client_map_df['cliente'].unique())
                    
                    sel_cl_name = st.selectbox("Seleccionar Cliente:", cl_list)
                    
                    if sel_cl_name:
                        sel_cl_id = client_map[sel_cl_name]
                        c_dat = dff[dff['clienteid'] == sel_cl_id]
                        
                        c_tot = c_dat['monto_real'].sum()
                        c_last = c_dat['fecha'].max()
                        days = (dff['fecha'].max() - c_last).days
                        weeks = c_dat['semana_anio'].nunique()
                        freq = c_dat['id_transaccion'].nunique() / weeks if weeks > 0 else 0

                        st.info(f"Cliente: **{sel_cl_name}**")
                        m1, m2 = st.columns(2)
                        m1.metric("Total", f"${c_tot:,.0f}")
                        m2.metric("Frecuencia", f"{freq:.1f} /sem")
                        st.write(f"📅 Última: {c_last.strftime('%d-%m-%Y')}")
                        if days > 7: st.error(f"🚨 Inactivo hace {days} días")
                        else: st.success(f"✅ Activo")
            
            with cc2:
                if 'cliente' in dff.columns and 'producto' in dff.columns and sel_cl_name:
                    st.markdown(f"#### 📦 ¿Qué compra {sel_cl_name}?")
                    top_p_client = c_dat.groupby('producto')['monto_real'].sum().reset_index().sort_values('monto_real', ascending=False).head(10).reset_index()
                    fig_cl_prod = px.bar(top_p_client, x='monto_real', y='producto', orientation='h', text_auto='.2s', color='monto_real', color_continuous_scale='Teal')
                    st.plotly_chart(fig_cl_prod, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 🚨 Alerta de Fuga")
            if 'clienteid' in dff.columns and not dff['clienteid'].empty:
                w1_end = df_v['fecha'].min() + datetime.timedelta(days=7)
                w_last = df_v['fecha'].max() - datetime.timedelta(days=7)
                start_cl = set(dff[dff['fecha'] <= w1_end]['clienteid'].unique())
                end_cl = set(dff[dff['fecha'] >= w_last]['clienteid'].unique())
                churn_ids = list(start_cl - end_cl)
                
                risk_df_temp = dff[dff['clienteid'].isin(churn_ids)].groupby(['cliente', 'vendedor'])['monto_real'].sum().reset_index()
                st.error(f"⚠️ {len(churn_ids)} Clientes no recompraron la última semana")
                st.dataframe(risk_df_temp.sort_values('monto_real', ascending=False).head(10), use_container_width=True)
            else: st.warning("No hay datos para esta vista.")

        # 6. AUDITORÍA
        with tabs[5]:
            st.header("🕵️ Mapa de Oportunidades (Gaps)")
            if not dff.empty:
                if 'jerarquia1' in dff.columns: col_cat = 'jerarquia1'
                else: col_cat = 'categoria'
                pivot = dff.groupby(['vendedor', col_cat])['monto_real'].sum().reset_index().pivot(index='vendedor', columns=col_cat, values='monto_real').fillna(0)
                st.plotly_chart(px.imshow(pivot, text_auto='.2s', aspect="auto", color_continuous_scale='Blues'), use_container_width=True)
            else: st.warning("No hay datos para esta vista.")

        # 7. INTELIGENCIA
        with tabs[6]:
            st.header("🧠 Recomendador")
            if not dff.empty:
                if 'producto' in dff.columns and 'id_transaccion' in dff.columns:
                    st.subheader("Cross-Selling (Productos relacionados)")
                    prods = dff.groupby('producto')['monto_real'].sum().sort_values(ascending=False).head(50).index
                    sel_p = st.selectbox("Si el cliente lleva...", prods)
                    if sel_p:
                        txs = dff[dff['producto'] == sel_p]['id_transaccion'].unique()
                        sub = dff[dff['id_transaccion'].isin(txs)]
                        sub = sub[sub['producto'] != sel_p]
                        if not sub.empty:
                            rel = sub.groupby('producto')['id_transaccion'].nunique().reset_index().sort_values('id_transaccion', ascending=False).head(5)
                            st.success("👉 Ofrécele también:")
                            st.table(rel.set_index('producto'))
                        else: st.info("No se encontraron productos relacionados en las transacciones.")
                else: st.warning("Faltan columnas 'producto' o 'id_transaccion'.")
            else: st.warning("No hay datos suficientes para esta vista.")


else:
    # 🚨 ERROR SI NO ENCUENTRA EL ARCHIVO PRINCIPAL
    st.error("🚨 ERROR CRÍTICO: No se pudo cargar el archivo de ventas principal ('venta_completa.csv').")
