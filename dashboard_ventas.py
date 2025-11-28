import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Hupa Dashboard", page_icon="🚛", layout="wide")

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

# --- FUNCIÓN: BUSCADOR DE ARCHIVOS ---
def find_file_fuzzy(keywords):
    current_files = os.listdir('.')
    for f in current_files:
        if all(k.lower() in f.lower() for k in keywords) and (f.endswith('.csv') or f.endswith('.xlsx')):
            return f
    return None

# --- FUNCIÓN DE LECTURA ROBUSTA ---
@st.cache_data
def load_consolidated_data():
    
    file_venta = find_file_fuzzy(['venta', 'completa'])
    file_preventa = find_file_fuzzy(['preventa'])
    file_maestro = find_file_fuzzy(['maestro', 'cliente'])
    file_rebotes = find_file_fuzzy(['rebotes'])
    
    df_v, df_p, df_a, df_r = None, None, None, None
    
    def read_smart(file_path):
        if not file_path: return None
        try:
            df = pd.read_csv(file_path, sep=';', on_bad_lines='skip', encoding='utf-8')
            if df.shape[1] < 2: 
                df = pd.read_csv(file_path, sep=',', on_bad_lines='skip', encoding='utf-8')
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            return df
        except: return None

    # 1. CARGAR VENTA
    if file_venta:
        df_v = read_smart(file_venta)
        if df_v is not None and 'fecha' in df_v.columns:
            if 'clienteid' in df_v.columns: df_v['clienteid'] = df_v['clienteid'].astype(str)
            if 'cliente' in df_v.columns: df_v['cliente'] = df_v['cliente'].astype(str).str.strip().str.upper()
            if 'cluster' in df_v.columns: df_v['cluster'] = df_v['cluster'].fillna('Sin Cluster')
            
            df_v['fecha'] = pd.to_datetime(df_v['fecha'], format='%d/%m/%Y', dayfirst=True, errors='coerce')
            df_v['semana_anio'] = df_v['fecha'].dt.isocalendar().week
            
            if 'montofinal' in df_v.columns: df_v['monto_real'] = df_v['montofinal']
            elif 'monto' in df_v.columns: df_v['monto_real'] = df_v['monto']
            else: df_v['monto_real'] = 0
            
            df_v['id_transaccion'] = df_v.get('ventaid', df_v.columns[0])
            
            cat_map = {
                'JOSE CARLOS MENDOZA MENDOZA': '1. MAYORISTAS', 'KEVIN  COLODRO VACA': '1. MAYORISTAS',
                'MARCIA MARAZ MONTAÑO': '1. MAYORISTAS', 'ABDY JOSE RUUD': '1. MAYORISTAS',
                'MARIBEL ROLLANO CHOQUE': '2. PERIFERIA', 'RAFAEL SARDAN SALAZAR': '3. FARMACIAS',
                'LUIS PABLO LOPEZ NEGRETE': '4. INSTITUCIONAL', 'JAVIER JUSTINIANO GOMEZ': '5. PARETOS TDB'
            }
            df_v['canal'] = df_v['vendedor'].map(cat_map).fillna('6. RUTA TDB')

    # 2. CARGAR MAESTRO
    if file_maestro:
        df_a = read_smart(file_maestro)
        if df_a is not None:
            col_id = next((c for c in df_a.columns if 'cliente' in c and 'id' in c), None)
            col_vend = next((c for c in df_a.columns if 'vendedor' in c), None)
            col_nom = next((c for c in df_a.columns if 'cliente' in c and 'id' not in c), None)
            
            if col_id and col_vend:
                rename_dict = {col_id: 'clienteid', col_vend: 'vendedor'}
                if col_nom: rename_dict[col_nom] = 'cliente'
                
                df_a = df_a.rename(columns=rename_dict)
                df_a['clienteid'] = df_a['clienteid'].astype(str)
                df_a['vendedor'] = df_a['vendedor'].astype(str).str.strip()
                
                if 'cliente' not in df_a.columns:
                    df_a['cliente'] = "Cliente " + df_a['clienteid']
                
                if 'latitud' in df_a.columns and 'longitud' in df_a.columns:
                    df_a['latitud'] = pd.to_numeric(df_a['latitud'].astype(str).str.replace(',', '.'), errors='coerce')
                    df_a['longitud'] = pd.to_numeric(df_a['longitud'].astype(str).str.replace(',', '.'), errors='coerce')
                    df_a = df_a.dropna(subset=['latitud', 'longitud'])
                    df_a = df_a[(df_a['latitud'] != 0) & (df_a['longitud'] != 0)]

    # 3. CARGAR PREVENTA
    if file_preventa:
        df_p = read_smart(file_preventa)
        if df_p is not None and 'fecha' in df_p.columns:
            df_p['fecha'] = pd.to_datetime(df_p['fecha'], format='%d/%m/%Y', dayfirst=True, errors='coerce')
            if 'monto_final' in df_p.columns: df_p['monto_pre'] = df_p['monto_final']
            elif 'monto' in df_p.columns: df_p['monto_pre'] = df_p['monto']
            else: df_p['monto_pre'] = 0
            col_pre = next((c for c in df_p.columns if 'nro' in c and 'preventa' in c), None)
            if col_pre: df_p['id_cruce'] = df_p[col_pre]
    
    # 4. CARGAR REBOTES
    if file_rebotes:
        df_r = read_smart(file_rebotes)
        if df_r is not None:
            col_fecha_entrega = next((c for c in df_r.columns if 'entrega' in c and 'fecha' in c), None)
            if not col_fecha_entrega: col_fecha_entrega = next((c for c in df_r.columns if 'fecha' in c), None)
            if col_fecha_entrega:
                df_r['fecha_filtro'] = pd.to_datetime(df_r[col_fecha_entrega], format='%d/%m/%Y', dayfirst=True, errors='coerce')
            if 'vendedor' in df_r.columns:
                df_r['vendedor'] = df_r['vendedor'].astype(str).str.strip().str.upper()
            col_monto_r = next((c for c in df_r.columns if 'monto' in c and 'rechazo' in c), None)
            if col_monto_r:
                df_r['monto_rechazo'] = pd.to_numeric(df_r[col_monto_r], errors='coerce').fillna(0)

    # ENRIQUECIMIENTO
    if df_v is not None and df_a is not None:
        df_v = df_v.rename(columns={'vendedor': 'vendedor_venta'})
        temp_a = df_a[['clienteid', 'vendedor']].drop_duplicates(subset=['clienteid'])
        df_v = pd.merge(df_v, temp_a, on='clienteid', how='left')
        df_v['vendedor'] = df_v['vendedor'].fillna(df_v['vendedor_venta'])
        df_v['canal'] = df_v['vendedor'].map(cat_map).fillna('6. RUTA TDB')

    return df_v, df_p, df_a, df_r

# --- INTERFAZ ---
with st.sidebar:
    st.title("🚛 Hupa Dashboard")
    st.success("KPIs de Cluster Activos")
    st.markdown("---")
    meta = st.number_input("Meta Mensual ($)", value=2500000, step=100000)

df_v, df_p, df_a, df_r = load_consolidated_data()

if df_v is not None:
    
    # --- FILTROS ---
    col_filt1, col_filt2 = st.sidebar.columns(2)
    canales_list = sorted(df_v['canal'].dropna().unique().tolist())
    sel_canal = st.sidebar.multiselect("Filtrar por Canal:", canales_list, default=canales_list)
    
    dff_canal = df_v[df_v['canal'].isin(sel_canal)].copy()
    vendedores_list = sorted(dff_canal['vendedor'].dropna().unique().tolist())
    sel_vendedor = st.sidebar.selectbox("Filtrar por Vendedor:", ["Todos"] + vendedores_list)
    
    if sel_vendedor != "Todos":
        dff = dff_canal[dff_canal['vendedor'] == sel_vendedor].copy()
        if df_a is not None: df_a_filt = df_a[df_a['vendedor'] == sel_vendedor]
        if df_p is not None: df_p_filt = df_p[df_p['vendedor'] == sel_vendedor]
        if df_r is not None: df_r_filt = df_r[df_r['vendedor'] == sel_vendedor]
    else:
        dff = dff_canal.copy()
        if df_a is not None: df_a_filt = df_a[df_a['vendedor'].isin(vendedores_list)]
        if df_p is not None: df_p_filt = df_p[df_p['vendedor'].isin(vendedores_list)]
        if df_r is not None: df_r_filt = df_r.copy()
    
    tot = dff['monto_real'].sum()
    cob = dff['clienteid'].nunique()
    trx = dff['id_transaccion'].nunique()
    ticket = tot/trx if trx>0 else 0
    
    # --- HEADER KPIs (CON VELOCIMETRO y CLUSTER) ---
    c_gauge, c_kpis = st.columns([1, 2])
    
    with c_gauge:
        current_meta = meta if sel_vendedor == "Todos" else (meta/10)
        fig_g = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = tot,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Progreso Meta", 'font': {'size': 16}},
            delta = {'reference': current_meta, 'increasing': {'color': "green"}},
            gauge = {
                'axis': {'range': [None, current_meta*1.2]},
                'bar': {'color': "#2C3E50"},
                'steps': [{'range': [0, current_meta*0.7], 'color': '#ffeeee'}, {'range': [current_meta*0.7, current_meta], 'color': '#fff8e1'}],
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': current_meta}}))
        fig_g.update_layout(height=250, margin=dict(t=30,b=10,l=30,r=30))
        st.plotly_chart(fig_g, use_container_width=True)
        
    with c_kpis:
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Calculo Cluster Lider
        has_cluster = 'cluster' in dff.columns
        ck1, ck2, ck3, ck4 = st.columns(4)
        
        with ck1:
            st.markdown(f"""<div class="metric-card"><div class="metric-title">Ventas Totales</div><div class="metric-value">${tot:,.0f}</div><div class="metric-delta delta-pos">Actual</div></div>""", unsafe_allow_html=True)
        with ck2:
            st.markdown(f"""<div class="metric-card"><div class="metric-title">Cobertura</div><div class="metric-value">{cob}</div><div class="metric-delta delta-neu">Clientes</div></div>""", unsafe_allow_html=True)
        with ck3:
            st.markdown(f"""<div class="metric-card"><div class="metric-title">Ticket Promedio</div><div class="metric-value">${ticket:,.0f}</div><div class="metric-delta delta-neu">Por Venta</div></div>""", unsafe_allow_html=True)
        
        # TARJETA CLUSTER (NUEVA)
        with ck4:
            if has_cluster and not dff.empty:
                top_cluster = dff.groupby('cluster')['monto_real'].sum().sort_values(ascending=False).head(1)
                cl_name = top_cluster.index[0] if not top_cluster.empty else "N/A"
                cl_val = top_cluster.iloc[0] if not top_cluster.empty else 0
                st.markdown(f"""<div class="metric-card"><div class="metric-title">Cluster Líder</div><div class="metric-value" style="font-size: 1.2rem;">{cl_name}</div><div class="metric-delta delta-pos">${cl_val:,.0f}</div></div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="metric-card"><div class="metric-title">Cluster Líder</div><div class="metric-value">-</div><div class="metric-delta">Sin Datos</div></div>""", unsafe_allow_html=True)
            
        # Rechazo KPI
        rechazo_val = 0
        if df_p is not None and 'monto_pre' in df_p_filt.columns:
            rechazo_val = df_p_filt['monto_pre'].sum() - tot
            st.markdown(f'<div class="alert-box alert-warning" style="margin-top:10px;">📉 <b>Rechazo Estimado:</b> ${rechazo_val:,.0f}</div>', unsafe_allow_html=True)

    st.markdown("---")
    
    tabs = st.tabs(["🚫 Rebotes", "🎯 Cobertura", "📅 Frecuencia", "🗺️ Mapa Ruta", "📉 Caída", "🎮 Simulador", "📈 Estrategia", "💳 Finanzas", "👥 Clientes", "🔍 Auditoría", "🧠 Inteligencia"])
    
    # 0. REBOTES
    with tabs[0]:
        st.header("🚫 Análisis de Rebotes")
        if df_r is not None:
            c_fr1, c_fr2, c_fr3 = st.columns(3)
            distribuidores = sorted(df_r['distribuidor'].dropna().unique()) if 'distribuidor' in df_r.columns else []
            zonas = sorted(df_r['zona'].dropna().unique()) if 'zona' in df_r.columns else []
            min_d_r = df_r['fecha_filtro'].min().date() if 'fecha_filtro' in df_r.columns else None
            max_d_r = df_r['fecha_filtro'].max().date() if 'fecha_filtro' in df_r.columns else None
            
            with c_fr1: sel_distribuidor = st.multiselect("Distribuidor:", distribuidores)
            with c_fr2: sel_zona = st.multiselect("Zona:", zonas)
            with c_fr3:
                if min_d_r and max_d_r: sel_fecha = st.date_input("Fecha Entrega:", [min_d_r, max_d_r])
                else: sel_fecha = None

            df_r_local = df_r.copy()
            if sel_vendedor != "Todos": df_r_local = df_r_local[df_r_local['vendedor'] == sel_vendedor]
            if sel_distribuidor: df_r_local = df_r_local[df_r_local['distribuidor'].isin(sel_distribuidor)]
            if sel_zona: df_r_local = df_r_local[df_r_local['zona'].isin(sel_zona)]
            if sel_fecha and len(sel_fecha) == 2 and 'fecha_filtro' in df_r_local.columns:
                 df_r_local = df_r_local[(df_r_local['fecha_filtro'].dt.date >= sel_fecha[0]) & (df_r_local['fecha_filtro'].dt.date <= sel_fecha[1])]

            total_rechazo = df_r_local['monto_rechazo'].sum()
            cant_rebotes = len(df_r_local)
            
            mr1, mr2 = st.columns(2)
            mr1.markdown(f'<div class="alert-box alert-danger">💰 <b>Monto Rechazado:</b> ${total_rechazo:,.0f}</div>', unsafe_allow_html=True)
            mr2.markdown(f'<div class="alert-box alert-warning">📦 <b>Cantidad Rebotes:</b> {cant_rebotes}</div>', unsafe_allow_html=True)
            
            col_reb1, col_reb2 = st.columns([1, 2])
            with col_reb1:
                col_motivo = next((c for c in df_r_local.columns if 'motivo' in c), None)
                if col_motivo:
                    rechazo_motivo = df_r_local[col_motivo].value_counts().reset_index()
                    rechazo_motivo.columns = ['Motivo', 'Cantidad']
                    fig_pie_r = px.pie(rechazo_motivo, values='Cantidad', names='Motivo', title="Motivos de Rechazo", color_discrete_sequence=px.colors.sequential.RdBu)
                    st.plotly_chart(fig_pie_r, use_container_width=True)
                else: st.info("Sin columna 'Motivo'")

            with col_reb2:
                if sel_vendedor == "Todos":
                    rebotes_vend = df_r_local.groupby('vendedor')['monto_rechazo'].sum().sort_values(ascending=False).reset_index()
                    fig_bar_r = px.bar(rebotes_vend, x='monto_rechazo', y='vendedor', orientation='h', 
                                       title="Rechazo por Vendedor", text_auto='.2s', color='monto_rechazo', color_continuous_scale='Reds')
                    st.plotly_chart(fig_bar_r, use_container_width=True)
                else:
                    st.subheader("Detalle")
                    cols_view = [c for c in ['fecha_filtro', 'distribuidor', 'zona', 'cliente', 'monto_rechazo', 'motivo_rechazo'] if c in df_r_local.columns]
                    st.dataframe(df_r_local[cols_view].sort_values('monto_rechazo', ascending=False), use_container_width=True)
            
            st.subheader("📋 Listado Completo de Rebotes (Filtrado)")
            st.dataframe(df_r_local, use_container_width=True)
        else: st.warning("Carga 'rebotes.csv'.")

    # 1. PENETRACIÓN
    with tabs[1]:
        if df_a is not None:
            st.header("🎯 Cobertura de Cartera")
            total_asig = df_a_filt['clienteid'].nunique()
            total_serv = dff['clienteid'].nunique()
            total_no_serv = total_asig - total_serv
            efectividad = (total_serv / total_asig * 100) if total_asig > 0 else 0
            kp1, kp2, kp3, kp4 = st.columns(4)
            kp1.metric("Cartera Total", total_asig)
            kp2.metric("Visitados", total_serv)
            kp3.metric("No Visitados", total_no_serv)
            kp4.metric("Efectividad", f"{efectividad:.1f}%")
            if sel_vendedor == "Todos":
                asig = df_a_filt.groupby('vendedor')['clienteid'].nunique().reset_index(name='Asignados')
                serv = dff.groupby('vendedor')['clienteid'].nunique().reset_index(name='Servidos')
                pen = pd.merge(asig, serv, on='vendedor', how='left').fillna(0)
                pen['% Pen'] = (pen['Servidos'] / pen['Asignados'].replace(0, 1)) * 100
                pen['Gap'] = pen['Asignados'] - pen['Servidos']
                st.dataframe(pen.sort_values('% Pen', ascending=False).style.format({'% Pen': '{:.1f}%'}), use_container_width=True)
                fig_p = go.Figure(data=[
                    go.Bar(name='Servidos', y=pen['vendedor'], x=pen['Servidos'], orientation='h', marker_color='#2ECC71', text=pen['Servidos'], textposition='auto'),
                    go.Bar(name='Sin Compra', y=pen['vendedor'], x=pen['Gap'], orientation='h', marker_color='#E74C3C', text=pen['Gap'], textposition='auto')
                ])
                fig_p.update_layout(barmode='stack', height=500, title="Cobertura de Cartera")
                st.plotly_chart(fig_p, use_container_width=True)
            else:
                st.subheader(f"📋 Detalle - {sel_vendedor}")
                clientes_maestro = df_a_filt[['clienteid', 'cliente']].drop_duplicates()
                clientes_con_compra = set(dff['clienteid'].unique())
                clientes_maestro['Estado'] = clientes_maestro['clienteid'].apply(lambda x: '✅ Visitado' if x in clientes_con_compra else '❌ Pendiente')
                st.dataframe(clientes_maestro.sort_values('Estado', ascending=False), use_container_width=True)
        else: st.warning("Carga 'Maestro_de_clientes.csv'.")

    # 2. FRECUENCIA
    with tabs[2]:
        st.header("📅 Frecuencia")
        if df_a is not None:
            cartera_total = df_a_filt[['clienteid', 'cliente', 'vendedor']].drop_duplicates(subset=['clienteid'])
            freq_sales = dff.groupby(['clienteid'])['fecha'].nunique().reset_index(name='frecuencia_real')
            df_freq = pd.merge(cartera_total, freq_sales, on='clienteid', how='left').fillna(0)
            def clasificar(f):
                if f == 0: return 'Sin Compra (0)'
                elif f < 3: return 'Baja (<3)'
                elif f <= 5: return 'En Modelo (3-5)'
                else: return 'Alta (>5)'
            df_freq['Estado'] = df_freq['frecuencia_real'].apply(clasificar)
            total_cartera = len(df_freq)
            en_modelo = len(df_freq[df_freq['Estado'] == 'En Modelo (3-5)'])
            fuera_modelo = total_cartera - en_modelo
            k1, k2, k3 = st.columns(3)
            k1.metric("Cartera", f"{total_cartera}")
            k2.metric("En Modelo (3-5)", f"{en_modelo}")
            k3.metric("Fuera Modelo", f"{fuera_modelo}", delta_color="inverse")
            c_f1, c_f2 = st.columns([1, 2])
            with c_f1:
                resumen = df_freq['Estado'].value_counts().reset_index()
                resumen.columns = ['Estado', 'Count']
                fig_pie_freq = px.pie(resumen, values='Count', names='Estado', title="Distribución", color='Estado', 
                                      color_discrete_map={'Sin Compra (0)': '#95A5A6', 'Baja (<3)': '#E74C3C', 'En Modelo (3-5)': '#2ECC71', 'Alta (>5)': '#3498DB'})
                st.plotly_chart(fig_pie_freq, use_container_width=True)
            with c_f2:
                freq_vend = df_freq.groupby(['vendedor', 'Estado']).size().reset_index(name='Count')
                total_vend = freq_vend.groupby('vendedor')['Count'].transform('sum')
                freq_vend['Pct'] = (freq_vend['Count'] / total_vend) * 100
                fig_bar_freq = px.bar(freq_vend, x='Pct', y='vendedor', color='Estado', orientation='h', 
                                   title="Cumplimiento por Vendedor (%)", text='Pct',
                                   color_discrete_map={'Sin Compra (0)': '#95A5A6', 'Baja (<3)': '#E74C3C', 'En Modelo (3-5)': '#2ECC71', 'Alta (>5)': '#3498DB'})
                fig_bar_freq.update_traces(texttemplate='%{text:.1f}%', textposition='inside')
                st.plotly_chart(fig_bar_freq, use_container_width=True)
            st.subheader("📋 Clientes Fuera de Modelo")
            tabla_baja = df_freq[df_freq['Estado'].isin(['Baja (<3)', 'Sin Compra (0)'])]
            st.dataframe(tabla_baja[['vendedor', 'clienteid', 'cliente', 'frecuencia_real', 'Estado']].sort_values('frecuencia_real'), use_container_width=True)
        else: st.warning("Carga Maestro.")

    # 3. MAPA
    with tabs[3]:
        if df_a is not None and 'latitud' in df_a.columns:
            st.header("🗺️ Mapa de Ruta")
            c_map1, c_map2 = st.columns([1, 3])
            with c_map1:
                dias_map = sorted(df_a['dia'].dropna().unique()) if 'dia' in df_a.columns else []
                s_dia = st.multiselect("Día Visita:", dias_map)
                df_map = df_a_filt.copy()
                if s_dia and 'dia' in df_map.columns: df_map = df_map[df_map['dia'].isin(s_dia)]
                clients_buy = set(dff['clienteid'].unique())
                df_map['Status'] = df_map['clienteid'].apply(lambda x: 'Con Compra' if x in clients_buy else 'Sin Compra')
                pendientes = df_map[df_map['Status'] == 'Sin Compra']
                if not pendientes.empty:
                    msg = f"🚨 *RUTA PENDIENTE*\n📉 Faltan: {len(pendientes)}\n\n"
                    for idx, row in pendientes.head(20).iterrows():
                        msg += f"❌ *{row['cliente']}*\n📍 https://www.google.com/maps/search/?api=1&query={row['latitud']},{row['longitud']}\n\n"
                    st.text_area("WhatsApp:", value=msg, height=300)
                else: st.success("¡Ruta Completa!")
            with c_map2:
                if not df_map.empty:
                    fig_map = px.scatter_mapbox(df_map, lat="latitud", lon="longitud", color="Status", 
                                                color_discrete_map={'Con Compra': '#2ECC71', 'Sin Compra': '#E74C3C'}, zoom=12)
                    fig_map.update_layout(mapbox_style="open-street-map", height=600)
                    st.plotly_chart(fig_map, use_container_width=True)
                    df_map['Link'] = df_map.apply(lambda row: f"https://www.google.com/maps/dir/?api=1&destination={row['latitud']},{row['longitud']}", axis=1)
                    st.dataframe(df_map[['cliente', 'Status', 'Link']].sort_values('Status'), column_config={"Link": st.column_config.LinkColumn("Ir", display_text="📍")}, use_container_width=True)
        else: st.warning("Falta Maestro con Coordenadas.")

    # 4. CAÍDA
    with tabs[4]:
        if df_p is not None:
            st.header("📉 Rechazos")
            ven_g = dff.groupby('preventaid')['monto_real'].sum().reset_index()
            pre_g = df_p_filt.groupby('id_cruce')['monto_pre'].sum().reset_index()
            m = pd.merge(pre_g, ven_g, left_on='id_cruce', right_on='preventaid', how='left').fillna(0)
            m['diff'] = m['monto_pre'] - m['monto_real']
            m['st'] = m.apply(lambda x: 'Entregado' if x['diff']<=5 else 'Rechazo', axis=1)
            c1, c2 = st.columns(2)
            fig_pie = px.pie(m, names='st', values='monto_pre', title="Estatus ($)")
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            c1.plotly_chart(fig_pie, use_container_width=True)
            m_det = pd.merge(df_p_filt, ven_g, left_on='id_cruce', right_on='preventaid', how='left').fillna(0)
            m_det['caida'] = m_det['monto_pre'] - m_det['monto_real']
            if sel_vendedor == "Todos":
                top_drop = m_det.groupby('vendedor')['caida'].sum().sort_values(ascending=False).head(10).reset_index()
                fig_bar = px.bar(top_drop, x='caida', y='vendedor', orientation='h', title="Top Rechazos", text='caida', color='caida', color_continuous_scale='Reds')
                fig_bar.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
                c2.plotly_chart(fig_bar, use_container_width=True)
            else:
                c2.metric("Monto Perdido", f"${m_det['caida'].sum():,.0f}")
        else: st.warning("Carga Preventas.")

    # 5. SIMULADOR
    with tabs[5]:
        st.header("🎮 Simulador")
        dl = max(0, 30 - df_v['fecha'].max().day)
        c1, c2 = st.columns(2)
        dt = c1.slider("Subir Ticket %", 0, 50, 0)
        dc = c2.slider("Subir Cobertura %", 0, 50, 0)
        d_avg = tot / df_v['fecha'].max().day
        proj = tot + (d_avg * (1+dt/100) * (1+dc/100) * dl)
        st.metric("Cierre Proyectado", f"${proj:,.0f}", f"{proj-meta:,.0f} vs Meta")

    # 6. ESTRATEGIA
    with tabs[6]:
        st.header("📈 Estrategia")
        # Gráfico Venta vs Clientes
        day = dff.groupby('fecha').agg({'monto_real':'sum', 'clienteid':'nunique'}).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=day['fecha'], y=day['monto_real'], name='Venta', marker_color='#95A5A6', text=day['monto_real'], texttemplate='$%{text:.2s}', textposition='auto'))
        fig.add_trace(go.Scatter(x=day['fecha'], y=day['clienteid'], name='Clientes', yaxis='y2', line=dict(color='#3498DB', width=3), mode='lines+markers+text', text=day['clienteid'], textposition='top center'))
        fig.update_layout(yaxis2=dict(overlaying='y', side='right'), title="Venta vs Clientes", height=600)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Gráfico Ventas por Cluster (NUEVO - Reemplazando o añadiendo)
        if 'cluster' in dff.columns:
            st.subheader("Ventas por Cluster")
            cluster_sales = dff.groupby('cluster')['monto_real'].sum().reset_index().sort_values('monto_real', ascending=True)
            fig_cluster = px.bar(cluster_sales, x='monto_real', y='cluster', orientation='h', title="Distribución por Cluster", text_auto='.2s', color='monto_real', color_continuous_scale='Viridis')
            st.plotly_chart(fig_cluster, use_container_width=True)
        
        if sel_vendedor == "Todos":
            st.markdown("---")
            sun = dff.groupby(['canal', 'vendedor'])['monto_real'].sum().reset_index()
            st.plotly_chart(px.sunburst(sun, path=['canal', 'vendedor'], values='monto_real'), use_container_width=True)

    # 7. FINANZAS
    with tabs[7]:
        st.header("💳 Finanzas")
        pay = dff.groupby('tipopago')['monto_real'].sum().reset_index()
        fig_pay = px.pie(pay, values='monto_real', names='tipopago', title="Mix Pago")
        fig_pay.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pay, use_container_width=True)
        if 'Crédito' in pay['tipopago'].values:
            cred = dff[dff['tipopago'].str.contains('Crédito', case=False, na=False)]
            st.dataframe(cred.groupby('vendedor')['monto_real'].sum().sort_values(ascending=False).head(10))

    # 8. CLIENTES
    with tabs[8]:
        st.header("👥 Clientes")
        c1, c2 = st.columns([1, 2])
        if 'cliente' in dff.columns:
            cli_map = dff[['cliente', 'clienteid']].drop_duplicates().set_index('cliente')['clienteid'].to_dict()
            cl_sel = c1.selectbox("Buscar:", sorted(cli_map.keys()))
            if cl_sel:
                cid = cli_map[cl_sel]
                cd = dff[dff['clienteid'] == cid]
                ctot = cd['monto_real'].sum()
                top_p = cd.groupby('producto')['monto_real'].sum().nlargest(10).reset_index()
                c1.metric("Total", f"${ctot:,.0f}")
                fig_cp = px.bar(top_p, x='monto_real', y='producto', orientation='h', title="Top Productos", text='monto_real')
                fig_cp.update_traces(texttemplate='$%{text:,.0f}', textposition='inside')
                c2.plotly_chart(fig_cp, use_container_width=True)
        w1 = df_v['fecha'].min() + datetime.timedelta(days=7)
        wl = df_v['fecha'].max() - datetime.timedelta(days=7)
        churn = list(set(dff[dff['fecha']<=w1]['clienteid']) - set(dff[dff['fecha']>=wl]['clienteid']))
        st.error(f"⚠️ {len(churn)} Clientes en Riesgo")
        if churn:
            churn_df = dff[dff['clienteid'].isin(churn)].groupby(['cliente', 'vendedor'])['monto_real'].sum().reset_index().sort_values('monto_real', ascending=False)
            st.dataframe(churn_df.head(10), use_container_width=True)

    # 9. AUDITORIA
    with tabs[9]:
        st.header("🔍 Auditoría")
        cf1, cf2, cf3 = st.columns(3)
        j1_o = sorted(dff['jerarquia1'].dropna().unique()) if 'jerarquia1' in dff.columns else []
        cat_o = sorted(dff['categoria'].dropna().unique()) if 'categoria' in dff.columns else []
        prod_o = sorted(dff['producto'].dropna().unique()) if 'producto' in dff.columns else []
        s_j1 = cf1.multiselect("Jerarquía 1", j1_o)
        s_cat = cf2.multiselect("Categoría", cat_o)
        s_prod = cf3.multiselect("Producto", prod_o)
        df_aud = dff.copy()
        if s_j1: df_aud = df_aud[df_aud['jerarquia1'].isin(s_j1)]
        if s_cat: df_aud = df_aud[df_aud['categoria'].isin(s_cat)]
        if s_prod: df_aud = df_aud[df_aud['producto'].isin(s_prod)]
        col_hm = 'producto' if s_prod else ('categoria' if s_cat else 'jerarquia1')
        if col_hm in df_aud.columns:
            piv = df_aud.groupby(['vendedor', col_hm])['monto_real'].sum().reset_index().pivot(index='vendedor', columns=col_hm, values='monto_real').fillna(0)
            st.plotly_chart(px.imshow(piv, aspect="auto", text_auto='.2s'), use_container_width=True)

    # 10. INTELIGENCIA
    with tabs[10]:
        st.header("🧠 Inteligencia")
        if 'producto' in dff.columns:
            tops = dff.groupby('producto')['monto_real'].sum().nlargest(50).index
            p_sel = st.selectbox("Si lleva...", tops)
            if p_sel:
                txs = dff[dff['producto']==p_sel]['id_transaccion'].unique()
                rel = dff[dff['id_transaccion'].isin(txs)]
                rel = rel[rel['producto']!=p_sel].groupby('producto')['id_transaccion'].nunique().nlargest(5)
                st.table(rel)

else:
    st.error("🚨 ERROR: No se encontró 'venta_completa.csv' en GitHub.")
