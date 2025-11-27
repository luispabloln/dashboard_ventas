import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Master Sales Command v35.0", page_icon="💎", layout="wide")

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
    st.title("💎 Master Dashboard v35.0")
    st.success("Resumen Penetración Activo")
    st.markdown("---")
    meta = st.number_input("Meta Mensual ($)", value=2500000, step=100000)

df_v, df_p, df_a = load_consolidated_data()

if df_v is not None:
    
    # --- FILTRO DE VENDEDOR UNIFICADO ---
    # Creamos un filtro de vendedor en el sidebar que afecta a todo el dashboard
    # Esto es mejor para ver el detalle "como en la imagen"
    vendedores_list = sorted(df_v['vendedor'].dropna().unique().tolist())
    sel_vendedor = st.sidebar.selectbox("Filtrar por Vendedor:", ["Todos"] + vendedores_list)
    
    # Aplicar filtro global
    if sel_vendedor != "Todos":
        dff = df_v[df_v['vendedor'] == sel_vendedor].copy()
        if df_a is not None: df_a_filt = df_a[df_a['vendedor'] == sel_vendedor]
        if df_p is not None: df_p_filt = df_p[df_p['vendedor'] == sel_vendedor]
    else:
        dff = df_v.copy()
        if df_a is not None: df_a_filt = df_a.copy()
        if df_p is not None: df_p_filt = df_p.copy()
    
    # KPIs
    tot = dff['monto_real'].sum()
    cob = dff['clienteid'].nunique()
    trx = dff['id_transaccion'].nunique()
    ticket = tot/trx if trx>0 else 0
    
    c1, c2 = st.columns([1, 2])
    with c1:
        fig_g = go.Figure(go.Indicator(mode="gauge+number+delta", value=tot, delta={'reference': meta if sel_vendedor == "Todos" else meta/len(vendedores_list)}, gauge={'axis':{'range':[None, meta*1.2 if sel_vendedor=="Todos" else (meta/len(vendedores_list))*1.2]}, 'bar':{'color':"#2C3E50"}}))
        fig_g.update_layout(height=200, margin=dict(t=20,b=20,l=30,r=30))
        st.plotly_chart(fig_g, use_container_width=True)
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        k1, k2, k3 = st.columns(3)
        k1.metric("Ventas", f"${tot:,.0f}")
        k2.metric("Cobertura", f"{cob}")
        k3.metric("Ticket", f"${ticket:,.0f}")
        if df_p is not None and 'monto_pre' in df_p_filt.columns:
            caida = df_p_filt['monto_pre'].sum() - tot
            st.markdown(f'<div class="alert-box alert-warning">📉 Rechazo Estimado: ${caida:,.0f}</div>', unsafe_allow_html=True)

    st.markdown("---")
    
    tabs = st.tabs(["🎯 Penetración", "📅 Frecuencia", "🗺️ Mapa Ruta", "📉 Caída", "🎮 Simulador", "📈 Estrategia", "💳 Finanzas", "👥 Clientes", "🔍 Auditoría", "🧠 Inteligencia"])
    
    # 1. PENETRACIÓN (CON RESUMEN TIPO IMAGEN)
    with tabs[0]:
        if df_a is not None:
            st.header("🎯 Penetración de Cartera")
            
            # CÁLCULO DE RESUMEN (LOS 4 CUADROS)
            total_clientes_asignados = df_a_filt['clienteid'].nunique()
            total_clientes_visitados = dff['clienteid'].nunique()
            total_no_visitados = total_clientes_asignados - total_clientes_visitados
            efectividad = (total_clientes_visitados / total_clientes_asignados * 100) if total_clientes_asignados > 0 else 0
            
            # MOSTRAR TARJETAS (COMO EN LA IMAGEN)
            kp1, kp2, kp3, kp4 = st.columns(4)
            kp1.metric("👥 Total Clientes", total_clientes_asignados)
            kp2.metric("✅ Visitados (Con Venta)", total_clientes_visitados)
            kp3.metric("❌ No Visitados", total_no_visitados)
            kp4.metric("📊 Efectividad", f"{efectividad:.1f}%")
            
            st.markdown("---")
            
            # Detalle si es "Todos" o Gráfico si es Individual
            if sel_vendedor == "Todos":
                # Tabla general por vendedor
                asig = df_a.groupby('vendedor')['clienteid'].nunique().reset_index(name='Asignados')
                serv = dff.groupby('vendedor')['clienteid'].nunique().reset_index(name='Servidos')
                pen = pd.merge(asig, serv, on='vendedor', how='left').fillna(0)
                pen['% Pen'] = (pen['Servidos'] / pen['Asignados'].replace(0, 1)) * 100
                pen['Gap'] = pen['Asignados'] - pen['Servidos']
                
                st.dataframe(pen.sort_values('% Pen', ascending=False).style.format({'% Pen': '{:.1f}%'}), use_container_width=True)
                
                fig_p = go.Figure(data=[
                    go.Bar(name='Servidos', y=pen['vendedor'], x=pen['Servidos'], orientation='h', marker_color='#2ECC71'),
                    go.Bar(name='Sin Compra', y=pen['vendedor'], x=pen['Gap'], orientation='h', marker_color='#E74C3C')
                ])
                fig_p.update_layout(barmode='stack', height=500, title="Cobertura por Vendedor")
                st.plotly_chart(fig_p, use_container_width=True)
            else:
                # Detalle de clientes (Lista) si es un solo vendedor
                st.subheader(f"📋 Listado de Clientes - {sel_vendedor}")
                
                # Cruzar maestro con ventas para ver quién falta
                clientes_maestro = df_a_filt[['clienteid', 'cliente']].drop_duplicates()
                clientes_con_compra = set(dff['clienteid'].unique())
                
                clientes_maestro['Estado'] = clientes_maestro['clienteid'].apply(lambda x: '✅ Visitado' if x in clientes_con_compra else '❌ Pendiente')
                
                # Mostrar primero los pendientes
                st.dataframe(
                    clientes_maestro.sort_values('Estado', ascending=False),
                    use_container_width=True
                )

        else: st.warning("Carga 'Maestro_de_clientes.csv'.")

    # 2. FRECUENCIA
    with tabs[1]:
        st.header("📅 Frecuencia de Compra")
        if df_a is not None:
            cartera_total = df_a_filt[['clienteid', 'cliente', 'vendedor']].drop_duplicates(subset=['clienteid'])
            freq_sales = dff.groupby(['clienteid'])['fecha'].nunique().reset_index(name='frecuencia_real')
            df_freq = pd.merge(cartera_total, freq_sales, on='clienteid', how='left').fillna(0)
            
            def clasificar(f):
                if f == 0: return 'Sin Compra (0)'
                elif f < 3: return 'Baja (<3)'
                elif f <= 5: return 'Ideal (3-5)'
                else: return 'Alta (>5)'
            
            df_freq['Estado'] = df_freq['frecuencia_real'].apply(clasificar)
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Cartera", len(df_freq))
            k2.metric("En Modelo (3-5)", len(df_freq[df_freq['Estado']=='En Modelo (3-5)']))
            k3.metric("Fuera de Modelo", len(df_freq[df_freq['Estado']!='En Modelo (3-5)']), delta_color="inverse")
            
            c_f1, c_f2 = st.columns([1, 2])
            with c_f1:
                resumen = df_freq['Estado'].value_counts().reset_index()
                resumen.columns = ['Estado', 'Count']
                st.plotly_chart(px.pie(resumen, values='Count', names='Estado', color='Estado', color_discrete_map={'Sin Compra (0)': '#95A5A6', 'Baja (<3)': '#E74C3C', 'En Modelo (3-5)': '#2ECC71', 'Alta (>5)': '#3498DB'}), use_container_width=True)
            with c_f2:
                st.dataframe(df_freq[['cliente', 'frecuencia_real', 'Estado']].sort_values('frecuencia_real'), use_container_width=True)
        else: st.warning("Carga Maestro.")

    # 3. MAPA
    with tabs[2]:
        if df_a is not None and 'latitud' in df_a.columns:
            st.header("🗺️ Mapa de Ruta")
            # Filtros adicionales solo para mapa
            dias_map = sorted(df_a['dia'].dropna().unique()) if 'dia' in df_a.columns else []
            s_dia = st.multiselect("Día Visita:", dias_map)
            
            df_map = df_a_filt.copy()
            if s_dia and 'dia' in df_map.columns: df_map = df_map[df_map['dia'].isin(s_dia)]
            
            if not df_map.empty:
                clients_buy = set(dff['clienteid'].unique())
                df_map['Status'] = df_map['clienteid'].apply(lambda x: 'Con Compra' if x in clients_buy else 'Sin Compra')
                
                fig_map = px.scatter_mapbox(df_map, lat="latitud", lon="longitud", color="Status", color_discrete_map={'Con Compra': '#2ECC71', 'Sin Compra': '#E74C3C'}, zoom=12)
                fig_map.update_layout(mapbox_style="open-street-map", height=500)
                st.plotly_chart(fig_map, use_container_width=True)
                
                if sel_vendedor != "Todos":
                    pendientes = df_map[df_map['Status'] == 'Sin Compra']
                    if not pendientes.empty:
                        msg = f"🚨 *RUTA {sel_vendedor}*\n📉 Faltan: {len(pendientes)}\n\n"
                        for idx, row in pendientes.head(20).iterrows():
                            msg += f"❌ *{row['cliente']}*\n📍 https://www.google.com/maps/search/?api=1&query={row['latitud']},{row['longitud']}\n\n"
                        st.text_area("WhatsApp:", value=msg, height=200)
            else: st.info("Sin clientes con coordenadas.")
        else: st.warning("Falta Lat/Lon en Maestro.")

    # 4. CAÍDA
    with tabs[3]:
        if df_p is not None and 'id_cruce' in df_p_filt.columns:
            st.header("📉 Rechazos")
            ven_g = dff.groupby('preventaid')['monto_real'].sum().reset_index()
            pre_g = df_p_filt.groupby('id_cruce')['monto_pre'].sum().reset_index()
            m = pd.merge(pre_g, ven_g, left_on='id_cruce', right_on='preventaid', how='left').fillna(0)
            m['diff'] = m['monto_pre'] - m['monto_real']
            m['st'] = m.apply(lambda x: 'Entregado' if x['diff']<=5 else 'Rechazo', axis=1)
            st.plotly_chart(px.pie(m, names='st', values='monto_pre', title="Estatus ($)"), use_container_width=True)
        else: st.warning("Carga Preventas.")

    # 5. SIMULADOR
    with tabs[4]:
        st.header("🎮 Simulador")
        if not dff.empty:
            dl = max(0, 30 - df_v['fecha'].max().day)
            dt = st.slider("Ticket %", 0, 50, 0)
            dc = st.slider("Cobertura %", 0, 50, 0)
            d_avg = tot / df_v['fecha'].max().day
            proj = tot + (d_avg * (1+dt/100) * (1+dc/100) * dl)
            st.metric("Proyección", f"${proj:,.0f}", f"{proj-meta:,.0f} vs Meta")

    # 6. ESTRATEGIA
    with tabs[5]:
        st.header("📈 Estrategia")
        if not dff.empty:
            day = dff.groupby('fecha').agg({'monto_real':'sum', 'clienteid':'nunique'}).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Bar(x=day['fecha'], y=day['monto_real'], name='Venta', marker_color='#95A5A6'))
            fig.add_trace(go.Scatter(x=day['fecha'], y=day['clienteid'], name='Clientes', yaxis='y2', line=dict(color='#3498DB', width=3)))
            fig.update_layout(yaxis2=dict(overlaying='y', side='right'), title="Venta vs Clientes", height=500)
            st.plotly_chart(fig, use_container_width=True)

    # 7. FINANZAS
    with tabs[6]:
        st.header("💳 Finanzas")
        if not dff.empty:
            pay = dff.groupby('tipopago')['monto_real'].sum().reset_index()
            st.plotly_chart(px.pie(pay, values='monto_real', names='tipopago', title="Mix Pago"), use_container_width=True)

    # 8. CLIENTES
    with tabs[7]:
        st.header("👥 Clientes")
        if not dff.empty:
            cl_list = sorted(dff['cliente'].unique())
            cl_sel = st.selectbox("Buscar:", cl_list)
            if cl_sel:
                cd = dff[dff['cliente']==cl_sel]
                st.metric("Total", f"${cd['monto_real'].sum():,.0f}")
                st.plotly_chart(px.bar(cd.groupby('producto')['monto_real'].sum().nlargest(5).reset_index(), x='monto_real', y='producto', orientation='h'), use_container_width=True)

    # 9. AUDITORIA
    with tabs[8]:
        st.header("🔍 Auditoría")
        if not dff.empty:
            j1_o = sorted(dff['jerarquia1'].dropna().unique()) if 'jerarquia1' in dff.columns else []
            s_j1 = st.multiselect("Jerarquía 1", j1_o)
            df_aud = dff.copy()
            if s_j1: df_aud = df_aud[df_aud['jerarquia1'].isin(s_j1)]
            piv = df_aud.groupby(['vendedor', 'jerarquia1'])['monto_real'].sum().reset_index().pivot(index='vendedor', columns='jerarquia1', values='monto_real').fillna(0)
            st.plotly_chart(px.imshow(piv, aspect="auto", text_auto='.2s'), use_container_width=True)

    # 10. INTELIGENCIA
    with tabs[9]:
        st.header("🧠 Inteligencia")
        if not dff.empty:
            tops = dff.groupby('producto')['monto_real'].sum().nlargest(50).index
            p_sel = st.selectbox("Si lleva...", tops)
            if p_sel:
                txs = dff[dff['producto']==p_sel]['id_transaccion'].unique()
                rel = dff[dff['id_transaccion'].isin(txs)]
                rel = rel[rel['producto']!=p_sel].groupby('producto')['id_transaccion'].nunique().nlargest(5)
                st.table(rel)

else:
    st.error("🚨 ERROR: No se encontró 'venta_completa.csv' en GitHub.")
