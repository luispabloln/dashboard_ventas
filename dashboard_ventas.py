import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Master Sales Command v27.0", page_icon="💎", layout="wide")

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

# --- FUNCIÓN: BUSCADOR DE ARCHIVOS (CASE INSENSITIVE) ---
def find_file_fuzzy(keywords):
    current_files = os.listdir('.')
    for f in current_files:
        if all(k.lower() in f.lower() for k in keywords) and (f.endswith('.csv') or f.endswith('.xlsx')):
            return f
    return None

# --- FUNCIÓN DE LECTURA ROBUSTA ---
@st.cache_data
def load_consolidated_data():
    
    # 1. BUSCAR ARCHIVOS (Inteligente)
    file_venta = find_file_fuzzy(['venta', 'completa'])
    file_preventa = find_file_fuzzy(['preventa'])
    file_maestro = find_file_fuzzy(['maestro', 'cliente']) 
    
    df_v, df_p, df_a = None, None, None
    
    def read_smart(file_path):
        if not file_path: return None
        encodings = ['utf-8', 'latin-1', 'cp1252']
        separators = [';', ',']
        for enc in encodings:
            for sep in separators:
                try:
                    df = pd.read_csv(file_path, sep=sep, encoding=enc, on_bad_lines='skip')
                    if df.shape[1] > 1:
                        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
                        return df
                except: continue
        return None

    # CARGAR VENTA
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
            
            col_id = 'ventaid' if 'ventaid' in df_v.columns else df_v.columns[0]
            df_v['id_transaccion'] = df_v[col_id]
            
            # Canal Default
            cat_map = {
                'JOSE CARLOS MENDOZA MENDOZA': '1. MAYORISTAS', 'KEVIN  COLODRO VACA': '1. MAYORISTAS',
                'MARCIA MARAZ MONTAÑO': '1. MAYORISTAS', 'ABDY JOSE RUUD': '1. MAYORISTAS',
                'MARIBEL ROLLANO CHOQUE': '2. PERIFERIA', 'RAFAEL SARDAN SALAZAR': '3. FARMACIAS',
                'LUIS PABLO LOPEZ NEGRETE': '4. INSTITUCIONAL', 'JAVIER JUSTINIANO GOMEZ': '5. PARETOS TDB'
            }
            df_v['canal'] = df_v['vendedor'].map(cat_map).fillna('6. RUTA TDB')

    # CARGAR MAESTRO
    if file_maestro:
        df_a = read_smart(file_maestro)
        if df_a is not None:
            col_id = next((c for c in df_a.columns if 'cliente' in c and 'id' in c), None)
            col_vend = next((c for c in df_a.columns if 'vendedor' in c), None)
            if col_id and col_vend:
                df_a = df_a.rename(columns={col_id: 'clienteid', col_vend: 'vendedor'})
                df_a['clienteid'] = df_a['clienteid'].astype(str)
                df_a['vendedor'] = df_a['vendedor'].astype(str).str.strip()
                df_a = df_a[['clienteid', 'vendedor']].drop_duplicates(subset=['clienteid'])

    # CARGAR PREVENTA
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
        df_v = pd.merge(df_v, df_a[['clienteid', 'vendedor']], on='clienteid', how='left')
        df_v['vendedor'] = df_v['vendedor'].fillna(df_v['vendedor_venta'])
        df_v['canal'] = df_v['vendedor'].map(cat_map).fillna('6. RUTA TDB')

    return df_v, df_p, df_a

# --- FUNCIÓN PARA OBTENER FECHA MÁXIMA DE FORMA SEGURA ---
def get_max_date_safe(df):
    if df is not None and not df.empty and 'fecha' in df.columns:
        valid_dates = df['fecha'].dropna()
        if not valid_dates.empty:
            try: return valid_dates.max().strftime('%d-%m-%Y')
            except: return "Error"
    return "No disponible"

# --- INTERFAZ ---
with st.sidebar:
    st.title("💎 Master Dashboard v27.0")
    st.success("Sistema Full Restaurado")
    st.markdown("---")
    meta = st.number_input("Meta Mensual ($)", value=2500000, step=100000)

df_v, df_p, df_a = load_consolidated_data()

if df_v is not None:
    
    # FILTROS
    sel_canal = st.multiselect("Filtro Canal", df_v['canal'].unique(), default=df_v['canal'].unique())
    dff = df_v[df_v['canal'].isin(sel_canal)].copy()
    
    # KPIs
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
    
    # REPORTE SINCRONIZACION
    max_v = get_max_date_safe(df_v)
    max_p = get_max_date_safe(df_p)
    if max_v == max_p: st.markdown(f'<div class="alert-box alert-success">✅ Datos al día: {max_v}</div>', unsafe_allow_html=True)
    else: st.markdown(f'<div class="alert-box alert-warning">⚠️ Venta: {max_v} | Preventa: {max_p}</div>', unsafe_allow_html=True)

    # PESTAÑAS
    tabs = st.tabs(["🎯 Penetración", "📉 Caída", "🎮 Simulador", "📈 Estrategia", "💳 Finanzas", "👥 Clientes 360", "🔍 Auditoría", "🧠 Inteligencia"])
    
    # 1. PENETRACIÓN (FIXED GRAPH ERROR)
    with tabs[0]:
        if df_a is not None:
            st.header("🎯 Penetración de Cartera")
            v_list = dff['vendedor'].unique()
            df_a_filt = df_a[df_a['vendedor'].isin(v_list)]
            
            asig = df_a_filt.groupby('vendedor')['clienteid'].nunique().reset_index(name='Asignados')
            serv = dff.groupby('vendedor')['clienteid'].nunique().reset_index(name='Servidos')
            
            pen = pd.merge(asig, serv, on='vendedor', how='left').fillna(0)
            pen['% Pen'] = (pen['Servidos']/pen['Asignados'].replace(0,1))*100
            pen['Gap'] = pen['Asignados'] - pen['Servidos']
            
            st.dataframe(pen.sort_values('% Pen', ascending=False).style.format({'% Pen': '{:.1f}%'}), use_container_width=True)
            
            # --- CORRECCIÓN DEL GRÁFICO ---
            # Asegurar que el dataframe está ordenado para el gráfico
            pen_chart = pen.sort_values('Asignados', ascending=True)
            
            fig = go.Figure(data=[
                go.Bar(name='Servidos', y=pen_chart['vendedor'], x=pen_chart['Servidos'], orientation='h', marker_color='#2ECC71', text=pen_chart['Servidos'], textposition='auto'),
                go.Bar(name='Sin Compra', y=pen_chart['vendedor'], x=pen_chart['Gap'], orientation='h', marker_color='#E74C3C', text=pen_chart['Gap'], textposition='auto')
            ])
            fig.update_layout(barmode='stack', height=600, title="Cobertura de Cartera (Etiquetas Visibles)")
            st.plotly_chart(fig, use_container_width=True)
        else: st.warning("Carga 'Maestro_de_clientes.csv' para ver esto.")

    # 2. CAÍDA (Con Etiquetas)
    with tabs[1]:
        if df_p is not None:
            st.header("📉 Análisis de Rechazos")
            ven_g = dff.groupby('preventaid')['monto_real'].sum().reset_index()
            pre_g = df_p.groupby('id_cruce')['monto_pre'].sum().reset_index()
            m = pd.merge(pre_g, ven_g, left_on='id_cruce', right_on='preventaid', how='left').fillna(0)
            m['diff'] = m['monto_pre'] - m['monto_real']
            m['st'] = m.apply(lambda x: 'Entregado' if x['diff']<=5 else 'Rechazo', axis=1)
            
            c1, c2 = st.columns(2)
            fig_pie = px.pie(m, names='st', values='monto_pre', title="Estatus ($)")
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            c1.plotly_chart(fig_pie, use_container_width=True)
            
            m_det = pd.merge(df_p, ven_g, left_on='id_cruce', right_on='preventaid', how='left').fillna(0)
            m_det['caida'] = m_det['monto_pre'] - m_det['monto_real']
            top_drop = m_det.groupby('vendedor')['caida'].sum().sort_values(ascending=False).head(10).reset_index()
            fig_bar = px.bar(top_drop, x='caida', y='vendedor', orientation='h', title="Top Rechazos", text='caida', color='caida', color_continuous_scale='Reds')
            fig_bar.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
            c2.plotly_chart(fig_bar, use_container_width=True)
        else: st.warning("Carga 'preventa_completa.csv'.")

    # 3. SIMULADOR
    with tabs[2]:
        st.header("🎮 Simulador")
        dl = max(0, 30 - df_v['fecha'].max().day)
        c1, c2 = st.columns(2)
        dt = c1.slider("Subir Ticket %", 0, 50, 0)
        dc = c2.slider("Subir Cobertura %", 0, 50, 0)
        d_avg = tot / df_v['fecha'].max().day
        proj = tot + (d_avg * (1+dt/100) * (1+dc/100) * dl)
        st.metric("Cierre Proyectado", f"${proj:,.0f}", f"{proj-meta:,.0f} vs Meta")

    # 4. ESTRATEGIA (Con Etiquetas y ClienteID)
    with tabs[3]:
        st.header("📈 Estrategia")
        day = dff.groupby('fecha').agg({'monto_real':'sum', 'clienteid':'nunique'}).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=day['fecha'], y=day['monto_real'], name='Venta', marker_color='#95A5A6', text=day['monto_real'], texttemplate='$%{text:.2s}', textposition='auto'))
        fig.add_trace(go.Scatter(x=day['fecha'], y=day['clienteid'], name='Clientes', yaxis='y2', line=dict(color='#3498DB', width=3), mode='lines+markers+text', text=day['clienteid'], textposition='top center'))
        fig.update_layout(yaxis2=dict(overlaying='y', side='right'), title="Venta vs Clientes", height=600)
        st.plotly_chart(fig, use_container_width=True)
        
        sun = dff.groupby(['canal', 'vendedor'])['monto_real'].sum().reset_index()
        st.plotly_chart(px.sunburst(sun, path=['canal', 'vendedor'], values='monto_real'), use_container_width=True)

    # 5. FINANZAS (Con Etiquetas)
    with tabs[4]:
        st.header("💳 Finanzas")
        pay = dff.groupby('tipopago')['monto_real'].sum().reset_index()
        fig_pay = px.pie(pay, values='monto_real', names='tipopago', title="Mix Pago")
        fig_pay.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pay, use_container_width=True)
        if 'Crédito' in pay['tipopago'].values:
            cred = dff[dff['tipopago'].str.contains('Crédito', case=False, na=False)]
            st.write("Top Crédito")
            st.dataframe(cred.groupby('vendedor')['monto_real'].sum().sort_values(ascending=False).head(10))

    # 6. CLIENTES (Con Etiquetas y ClienteID)
    with tabs[5]:
        st.header("👥 Clientes 360°")
        c1, c2 = st.columns([1, 2])
        if 'cliente' in dff.columns:
            cli_map = dff[['cliente', 'clienteid']].drop_duplicates().set_index('cliente')['clienteid'].to_dict()
            cl_sel = c1.selectbox("Buscar Cliente:", sorted(cli_map.keys()))
            if cl_sel:
                cid = cli_map[cl_sel]
                cd = dff[dff['clienteid'] == cid]
                ctot = cd['monto_real'].sum()
                weeks = cd['semana_anio'].nunique()
                freq = cd['id_transaccion'].nunique() / weeks if weeks>0 else 0
                c1.info(f"{cl_sel}")
                c1.metric("Total", f"${ctot:,.0f}")
                c1.metric("Frecuencia", f"{freq:.1f} /sem")
                top_p = cd.groupby('producto')['monto_real'].sum().nlargest(10).reset_index()
                fig_cp = px.bar(top_p, x='monto_real', y='producto', orientation='h', title="Top Productos", text='monto_real')
                fig_cp.update_traces(texttemplate='$%{text:,.0f}', textposition='inside')
                c2.plotly_chart(fig_cp, use_container_width=True)
        
        w1 = df_v['fecha'].min() + datetime.timedelta(days=7)
        wl = df_v['fecha'].max() - datetime.timedelta(days=7)
        churn = list(set(dff[dff['fecha']<=w1]['clienteid']) - set(dff[dff['fecha']>=wl]['clienteid']))
        st.error(f"⚠️ {len(churn)} Clientes en Riesgo (Fuga)")
        if churn:
            churn_df = dff[dff['clienteid'].isin(churn)].groupby(['cliente', 'vendedor'])['monto_real'].sum().reset_index().sort_values('monto_real', ascending=False)
            st.dataframe(churn_df.head(10), use_container_width=True)

    # 7. AUDITORIA (Filtros Restaurados)
    with tabs[6]:
        st.header("🔍 Auditoría")
        cf1, cf2, cf3 = st.columns(3)
        j1_opt = sorted(dff['jerarquia1'].dropna().unique()) if 'jerarquia1' in dff.columns else []
        cat_opt = sorted(dff['categoria'].dropna().unique()) if 'categoria' in dff.columns else []
        prod_opt = sorted(dff['producto'].dropna().unique()) if 'producto' in dff.columns else []
        j2_opt = sorted(dff['jerarquia2'].dropna().unique()) if 'jerarquia2' in dff.columns else []
        j3_opt = sorted(dff['jerarquia3'].dropna().unique()) if 'jerarquia3' in dff.columns else []
        
        s_j1 = cf1.multiselect("Jerarquía 1", j1_opt)
        s_cat = cf1.multiselect("Categoría", cat_opt)
        s_j2 = cf2.multiselect("Jerarquía 2", j2_opt)
        s_prod = cf2.multiselect("Producto", prod_opt)
        s_j3 = cf3.multiselect("Jerarquía 3", j3_opt)
        
        df_aud = dff.copy()
        if s_j1: df_aud = df_aud[df_aud['jerarquia1'].isin(s_j1)]
        if s_j2: df_aud = df_aud[df_aud['jerarquia2'].isin(s_j2)]
        if s_j3: df_aud = df_aud[df_aud['jerarquia3'].isin(s_j3)]
        if s_cat: df_aud = df_aud[df_aud['categoria'].isin(s_cat)]
        if s_prod: df_aud = df_aud[df_aud['producto'].isin(s_prod)]
        
        col_hm = 'producto' if s_prod else ('categoria' if s_cat else ('jerarquia3' if s_j3 else ('jerarquia2' if s_j2 else 'jerarquia1')))
        if col_hm in df_aud.columns:
            piv = df_aud.groupby(['vendedor', col_hm])['monto_real'].sum().reset_index().pivot(index='vendedor', columns=col_hm, values='monto_real').fillna(0)
            st.plotly_chart(px.imshow(piv, aspect="auto", title=f"Mapa de Calor: Vendedor vs {col_hm}", text_auto='.2s'), use_container_width=True)

    # 8. INTELIGENCIA
    with tabs[7]:
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
