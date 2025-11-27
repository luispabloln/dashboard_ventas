import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Master Sales Command v33.0", page_icon="💎", layout="wide")

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
    
    df_v, df_p, df_a = None, None, None
    
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
            
            if col_id and col_vend:
                df_a = df_a.rename(columns={col_id: 'clienteid', col_vend: 'vendedor'})
                df_a['clienteid'] = df_a['clienteid'].astype(str)
                df_a['vendedor'] = df_a['vendedor'].astype(str).str.strip()
                
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

    # ENRIQUECIMIENTO
    if df_v is not None and df_a is not None:
        df_v = df_v.rename(columns={'vendedor': 'vendedor_venta'})
        temp_a = df_a[['clienteid', 'vendedor']].drop_duplicates(subset=['clienteid'])
        df_v = pd.merge(df_v, temp_a, on='clienteid', how='left')
        df_v['vendedor'] = df_v['vendedor'].fillna(df_v['vendedor_venta'])
        df_v['canal'] = df_v['vendedor'].map(cat_map).fillna('6. RUTA TDB')

    return df_v, df_p, df_a

# --- INTERFAZ ---
with st.sidebar:
    st.title("💎 Master Dashboard v33.0")
    st.success("Módulo Frecuencia Mejorado")
    st.markdown("---")
    meta = st.number_input("Meta Mensual ($)", value=2500000, step=100000)

df_v, df_p, df_a = load_consolidated_data()

if df_v is not None:
    
    sel_canal = st.multiselect("Filtro Canal", df_v['canal'].unique(), default=df_v['canal'].unique())
    dff = df_v[df_v['canal'].isin(sel_canal)].copy()
    
    tot = dff['monto_real'].sum()
    cob = dff['clienteid'].nunique()
    trx = dff['id_transaccion'].nunique()
    ticket = tot/trx if trx>0 else 0
    
    c1, c2 = st.columns([1, 2])
    with c1:
        fig_g = go.Figure(go.Indicator(mode="gauge+number+delta", value=tot, delta={'reference': meta}, gauge={'axis':{'range':[None, meta*1.2]}, 'bar':{'color':"#2C3E50"}}))
        fig_g.update_layout(height=200, margin=dict(t=20,b=20,l=30,r=30))
        st.plotly_chart(fig_g, use_container_width=True)
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        k1, k2, k3 = st.columns(3)
        k1.metric("Ventas", f"${tot:,.0f}")
        k2.metric("Cobertura", f"{cob}")
        k3.metric("Ticket", f"${ticket:,.0f}")
        if df_p is not None:
            caida = df_p['monto_pre'].sum() - tot
            st.markdown(f'<div class="alert-box alert-warning">📉 Rechazo Estimado: ${caida:,.0f}</div>', unsafe_allow_html=True)

    st.markdown("---")
    
    tabs = st.tabs(["📅 Frecuencia (NUEVO)", "🗺️ Mapa Ruta", "🎯 Penetración", "📉 Caída", "🎮 Simulador", "📈 Estrategia", "💳 Finanzas", "👥 Clientes", "🔍 Auditoría", "🧠 Inteligencia"])
    
    # 0. FRECUENCIA (CON MÉTRICAS DE CARTERA TOTAL)
    with tabs[0]:
        st.header("📅 Análisis de Frecuencia de Compra")
        
        if df_a is not None:
            # 1. Preparar la Cartera Total (Base Maestro)
            vendedores_activos = dff['vendedor'].unique()
            cartera_total = df_a[df_a['vendedor'].isin(vendedores_activos)].drop_duplicates(subset=['clienteid'])
            
            # 2. Calcular Frecuencia Real (Base Ventas)
            # Frecuencia = Cantidad de días distintos con compra
            freq_sales = dff.groupby(['clienteid'])['fecha'].nunique().reset_index(name='frecuencia_real')
            
            # 3. Cruzar Cartera con Frecuencia
            # Left join: Mantenemos todos los clientes del maestro. Si no compraron, frecuencia = 0
            df_freq_master = pd.merge(cartera_total, freq_sales, on='clienteid', how='left')
            df_freq_master['frecuencia_real'] = df_freq_master['frecuencia_real'].fillna(0)
            
            # 4. Clasificar
            def clasificar_modelo(f):
                if f == 0: return 'Sin Compra (0)'
                elif f < 3: return 'Baja (<3)'
                elif f <= 5: return 'En Modelo (3-5)'
                else: return 'Alta (>5)'
                
            df_freq_master['Estado'] = df_freq_master['frecuencia_real'].apply(clasificar_modelo)
            
            # 5. Métricas Resumen (KPIs)
            total_cartera = len(df_freq_master)
            en_modelo = len(df_freq_master[df_freq_master['Estado'] == 'En Modelo (3-5)'])
            fuera_modelo = total_cartera - en_modelo
            pct_modelo = (en_modelo / total_cartera * 100) if total_cartera > 0 else 0
            
            k1, k2, k3 = st.columns(3)
            k1.metric("👥 Cartera Total", f"{total_cartera}")
            k2.metric("✅ En Modelo (3-5)", f"{en_modelo}", f"{pct_modelo:.1f}%")
            k3.metric("❌ Fuera de Modelo", f"{fuera_modelo}", delta_color="inverse")
            
            st.markdown("---")

            # 6. Gráficos
            c_f1, c_f2 = st.columns([1, 2])
            
            with c_f1:
                # Torta General
                resumen_estado = df_freq_master['Estado'].value_counts().reset_index()
                resumen_estado.columns = ['Estado', 'Clientes']
                fig_pie = px.pie(resumen_estado, values='Clientes', names='Estado', title="Distribución de Frecuencia",
                                 color='Estado', 
                                 color_discrete_map={
                                     'Sin Compra (0)': '#95A5A6', 
                                     'Baja (<3)': '#E74C3C', 
                                     'En Modelo (3-5)': '#2ECC71', 
                                     'Alta (>5)': '#3498DB'
                                 })
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with c_f2:
                # Barra por Vendedor
                freq_by_vend = df_freq_master.groupby(['vendedor', 'Estado']).size().reset_index(name='Clientes')
                fig_bar = px.bar(freq_by_vend, x='Clientes', y='vendedor', color='Estado', orientation='h', 
                                 title="Cumplimiento de Modelo por Vendedor",
                                 color_discrete_map={
                                     'Sin Compra (0)': '#95A5A6', 
                                     'Baja (<3)': '#E74C3C', 
                                     'En Modelo (3-5)': '#2ECC71', 
                                     'Alta (>5)': '#3498DB'
                                 })
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # 7. Tabla de Acción
            st.subheader("📋 Clientes Fuera de Modelo (Frecuencia Baja)")
            filtro_vend = st.selectbox("Filtrar por Vendedor:", ["Todos"] + sorted(vendedores_activos.tolist()))
            
            tabla_baja = df_freq_master[df_freq_master['Estado'].isin(['Baja (<3)', 'Sin Compra (0)'])]
            
            if filtro_vend != "Todos":
                tabla_baja = tabla_baja[tabla_baja['vendedor'] == filtro_vend]
                
            # Traer nombre del cliente si es posible (del archivo de ventas o maestro si lo tiene)
            # Como el maestro tiene 'clienteid' pero no siempre 'cliente' nombre, intentamos recuperarlo de dff
            nombres = dff[['clienteid', 'cliente']].drop_duplicates(subset=['clienteid'])
            tabla_final = pd.merge(tabla_baja, nombres, on='clienteid', how='left')
            tabla_final['cliente'] = tabla_final['cliente'].fillna('Nombre no disponible')
            
            st.dataframe(tabla_final[['vendedor', 'clienteid', 'cliente', 'frecuencia_real', 'Estado']].sort_values('frecuencia_real'), use_container_width=True)
            
        else:
            st.warning("⚠️ Carga el archivo 'Maestro_de_clientes.csv' para ver el análisis de Cartera.")

    # 1. MAPA
    with tabs[1]:
        if df_a is not None and 'latitud' in df_a.columns:
            st.header("🗺️ Mapa de Cobertura")
            c_map1, c_map2 = st.columns([1, 2])
            with c_map1:
                vends_map = sorted(df_a['vendedor'].dropna().unique())
                s_vend = st.selectbox("Vendedor:", vends_map)
                dias_map = sorted(df_a['dia'].dropna().unique()) if 'dia' in df_a.columns else []
                s_dia = st.multiselect("Día:", dias_map)
                
                df_map = df_a[df_a['vendedor'] == s_vend].copy()
                if s_dia and 'dia' in df_map.columns: df_map = df_map[df_map['dia'].isin(s_dia)]
                
                clients_buy = set(dff['clienteid'].unique())
                df_map['Status'] = df_map['clienteid'].apply(lambda x: 'Con Compra' if x in clients_buy else 'Sin Compra')
                
                pendientes = df_map[df_map['Status'] == 'Sin Compra']
                if not pendientes.empty:
                    msg = f"🚨 *RUTA PENDIENTE - {s_vend}*\n📉 Faltan: {len(pendientes)}\n\n"
                    # Recuperar nombres de cliente para el mensaje (si no están en maestro, buscamos en dff aunque sea raro que estén en dff y no comprados, pero por si acaso o usar ID)
                    # Asumimos que el maestro puede no tener nombres legibles si solo usamos ID. Si tiene columna cliente, la usamos.
                    col_nom = next((c for c in df_map.columns if 'cliente' in c and 'id' not in c), None)
                    
                    for idx, row in pendientes.head(20).iterrows():
                        nom = row[col_nom] if col_nom else row['clienteid']
                        msg += f"❌ *{nom}*\n📍 https://www.google.com/maps/search/?api=1&query={row['latitud']},{row['longitud']}\n\n"
                    st.text_area("WhatsApp:", value=msg, height=300)
            
            with c_map2:
                if not df_map.empty:
                    fig_map = px.scatter_mapbox(df_map, lat="latitud", lon="longitud", color="Status", color_discrete_map={'Con Compra': '#2ECC71', 'Sin Compra': '#E74C3C'}, zoom=12)
                    fig_map.update_layout(mapbox_style="open-street-map", height=600)
                    st.plotly_chart(fig_map, use_container_width=True)
                    
                    # Tabla Detalle
                    if 'cliente' in df_map.columns:
                         # Link GMaps en tabla
                        df_map['Link'] = df_map.apply(lambda row: f"https://www.google.com/maps/dir/?api=1&destination={row['latitud']},{row['longitud']}", axis=1)
                        st.dataframe(
                            df_map[['cliente', 'Status', 'Link']].sort_values('Status'),
                            column_config={"Link": st.column_config.LinkColumn("Navegar", display_text="📍 Ir")},
                            use_container_width=True
                        )

    # 2. PENETRACIÓN
    with tabs[2]:
        if df_a is not None:
            st.header("🎯 Penetración")
            v_list = dff['vendedor'].unique()
            df_a_uniq = df_a[['clienteid', 'vendedor']].drop_duplicates()
            df_a_filt = df_a_uniq[df_a_uniq['vendedor'].isin(v_list)]
            asig = df_a_filt.groupby('vendedor')['clienteid'].nunique().reset_index(name='Asignados')
            serv = dff.groupby('vendedor')['clienteid'].nunique().reset_index(name='Servidos')
            pen = pd.merge(asig, serv, on='vendedor', how='left').fillna(0)
            pen['% Pen'] = (pen['Servidos'] / pen['Asignados'].replace(0, 1)) * 100
            pen['Gap'] = pen['Asignados'] - pen['Servidos']
            st.dataframe(pen.sort_values('% Pen', ascending=False).style.format({'% Pen': '{:.1f}%'}), use_container_width=True)
            pen = pen.sort_values('Asignados', ascending=True)
            fig_p = go.Figure(data=[
                go.Bar(name='Servidos', y=pen['vendedor'], x=pen['Servidos'], orientation='h', marker_color='#2ECC71', text=pen['Servidos'], textposition='auto'),
                go.Bar(name='Sin Compra', y=pen['vendedor'], x=pen['Gap'], orientation='h', marker_color='#E74C3C', text=pen['Gap'], textposition='auto')
            ])
            fig_p.update_layout(barmode='stack', height=600, title="Cobertura de Cartera")
            st.plotly_chart(fig_p, use_container_width=True)
        else: st.warning("Carga Maestro.")

    # 3. CAÍDA
    with tabs[3]:
        if df_p is not None:
            st.header("📉 Rechazos")
            ven_g = dff.groupby('preventaid')['monto_real'].sum().reset_index()
            pre_g = df_p.groupby('id_cruce')['monto_pre'].sum().reset_index()
            m = pd.merge(pre_g, ven_g, left_on='id_cruce', right_on='preventaid', how='left').fillna(0)
            m['diff'] = m['monto_pre'] - m['monto_real']
            m['st'] = m.apply(lambda x: 'Entregado' if x['diff']<=5 else 'Rechazo', axis=1)
            c1, c2 = st.columns(2)
            c1.plotly_chart(px.pie(m, names='st', values='monto_pre', title="Estatus"), use_container_width=True)
            m_det = pd.merge(df_p, ven_g, left_on='id_cruce', right_on='preventaid', how='left').fillna(0)
            m_det['caida'] = m_det['monto_pre'] - m_det['monto_real']
            top_drop = m_det.groupby('vendedor')['caida'].sum().sort_values(ascending=False).head(10).reset_index()
            c2.plotly_chart(px.bar(top_drop, x='caida', y='vendedor', orientation='h', title="$$ Perdidos", color='caida', color_continuous_scale='Reds'), use_container_width=True)
        else: st.warning("Carga Preventas.")

    # 4. SIMULADOR
    with tabs[4]:
        st.header("🎮 Simulador")
        dl = max(0, 30 - df_v['fecha'].max().day)
        c1, c2 = st.columns(2)
        dt = c1.slider("Subir Ticket %", 0, 50, 0)
        dc = c2.slider("Subir Cobertura %", 0, 50, 0)
        d_avg = tot / df_v['fecha'].max().day
        proj = tot + (d_avg * (1+dt/100) * (1+dc/100) * dl)
        st.metric("Cierre Proyectado", f"${proj:,.0f}", f"{proj-meta:,.0f} vs Meta")

    # 5. ESTRATEGIA
    with tabs[5]:
        st.header("📈 Estrategia")
        day = dff.groupby('fecha').agg({'monto_real':'sum', 'clienteid':'nunique'}).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=day['fecha'], y=day['monto_real'], name='Venta', marker_color='#95A5A6', text=day['monto_real'], texttemplate='$%{text:.2s}'))
        fig.add_trace(go.Scatter(x=day['fecha'], y=day['clienteid'], name='Clientes', yaxis='y2', line=dict(color='#3498DB', width=3), mode='lines+markers+text', text=day['clienteid'], textposition='top center'))
        fig.update_layout(yaxis2=dict(overlaying='y', side='right'), title="Venta vs Clientes", height=600)
        st.plotly_chart(fig, use_container_width=True)
        sun = dff.groupby(['canal', 'vendedor'])['monto_real'].sum().reset_index()
        st.plotly_chart(px.sunburst(sun, path=['canal', 'vendedor'], values='monto_real'), use_container_width=True)

    # 6. FINANZAS
    with tabs[6]:
        st.header("💳 Finanzas")
        pay = dff.groupby('tipopago')['monto_real'].sum().reset_index()
        st.plotly_chart(px.pie(pay, values='monto_real', names='tipopago', title="Mix Pago"), use_container_width=True)
        if 'Crédito' in pay['tipopago'].values:
            cred = dff[dff['tipopago'].str.contains('Crédito', case=False, na=False)]
            st.dataframe(cred.groupby('vendedor')['monto_real'].sum().sort_values(ascending=False).head(10))

    # 7. CLIENTES
    with tabs[7]:
        st.header("👥 Clientes")
        c1, c2 = st.columns([1, 2])
        if 'cliente' in dff.columns:
            cli_map = dff[['cliente', 'clienteid']].drop_duplicates().set_index('cliente')['clienteid'].to_dict()
            cl_sel = c1.selectbox("Buscar:", sorted(cli_map.keys()))
            if cl_sel:
                cid = cli_map[cl_sel]
                cd = dff[dff['clienteid'] == cid]
                ctot = cd['monto_real'].sum()
                weeks = cd['semana_anio'].nunique()
                freq = cd['id_transaccion'].nunique() / weeks if weeks>0 else 0
                c1.metric("Total", f"${ctot:,.0f}")
                c1.metric("Frecuencia", f"{freq:.1f} /sem")
                top_p = cd.groupby('producto')['monto_real'].sum().nlargest(10).reset_index()
                c2.plotly_chart(px.bar(top_p, x='monto_real', y='producto', orientation='h', title="Top Productos"), use_container_width=True)
        w1 = df_v['fecha'].min() + datetime.timedelta(days=7)
        wl = df_v['fecha'].max() - datetime.timedelta(days=7)
        churn = list(set(dff[dff['fecha']<=w1]['clienteid']) - set(dff[dff['fecha']>=wl]['clienteid']))
        st.error(f"⚠️ {len(churn)} Clientes en Riesgo")

    # 8. AUDITORIA
    with tabs[8]:
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

    # 9. INTELIGENCIA
    with tabs[9]:
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
