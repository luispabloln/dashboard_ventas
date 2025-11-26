import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Master Sales Command v22.2", page_icon="💎", layout="wide")

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
    """Busca un archivo en el directorio actual que contenga las palabras clave, ignorando mayúsculas."""
    current_files = os.listdir('.')
    for f in current_files:
        if all(k.lower() in f.lower() for k in keywords) and (f.endswith('.csv') or f.endswith('.xlsx')):
            return f
    return None

# --- FUNCIÓN DE LECTURA ROBUSTA ---
@st.cache_data
def load_consolidated_data():
    
    # BUSCAR ARCHIVOS AUTOMÁTICAMENTE
    file_venta = find_file_fuzzy(['venta', 'completa'])
    file_preventa = find_file_fuzzy(['preventa'])
    file_maestro = find_file_fuzzy(['maestro', 'cliente'])
    
    df_v, df_p, df_a = None, None, None
    
    def read_smart(file_path):
        if not file_path: return None
        
        # Intentos de lectura (UTF-8 y Latin-1 para tildes)
        encodings = ['utf-8', 'latin-1', 'cp1252']
        separators = [';', ',']
        
        for enc in encodings:
            for sep in separators:
                try:
                    if file_path.endswith('.xlsx'):
                        df = pd.read_excel(file_path)
                    else:
                        df = pd.read_csv(file_path, sep=sep, encoding=enc, on_bad_lines='skip')
                    
                    # Validación simple: si tiene más de 1 columna, es probable que esté bien leído
                    if df.shape[1] > 1:
                        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
                        return df
                except:
                    continue
        return None

    # 1. CARGAR VENTA
    if file_venta:
        df_v = read_smart(file_venta)
        if df_v is not None and 'fecha' in df_v.columns:
            # Limpieza
            if 'clienteid' in df_v.columns: df_v['clienteid'] = df_v['clienteid'].astype(str)
            if 'cliente' in df_v.columns: df_v['cliente'] = df_v['cliente'].astype(str).str.strip().str.upper()
            
            df_v['fecha'] = pd.to_datetime(df_v['fecha'], format='%d/%m/%Y', dayfirst=True, errors='coerce')
            df_v['semana_anio'] = df_v['fecha'].dt.isocalendar().week
            
            if 'montofinal' in df_v.columns: df_v['monto_real'] = df_v['montofinal']
            elif 'monto' in df_v.columns: df_v['monto_real'] = df_v['monto']
            else: df_v['monto_real'] = 0
            
            df_v['id_transaccion'] = df_v.get('ventaid', df_v.columns[0])
            
            # Canal por defecto
            cat_map = {
                'JOSE CARLOS MENDOZA MENDOZA': '1. MAYORISTAS', 'KEVIN  COLODRO VACA': '1. MAYORISTAS',
                'MARCIA MARAZ MONTAÑO': '1. MAYORISTAS', 'ABDY JOSE RUUD': '1. MAYORISTAS',
                'MARIBEL ROLLANO CHOQUE': '2. PERIFERIA', 'RAFAEL SARDAN SALAZAR': '3. FARMACIAS',
                'LUIS PABLO LOPEZ NEGRETE': '4. INSTITUCIONAL', 'JAVIER JUSTINIANO GOMEZ': '5. PARETOS TDB'
            }
            df_v['canal'] = df_v['vendedor'].map(cat_map).fillna('6. RUTA TDB')

    # 2. CARGAR MAESTRO (ASIGNACIONES)
    if file_maestro:
        df_a = read_smart(file_maestro)
        if df_a is not None:
            # Buscar columnas clave aunque tengan nombres raros
            col_id = next((c for c in df_a.columns if 'cliente' in c and 'id' in c), None)
            col_vend = next((c for c in df_a.columns if 'vendedor' in c), None)
            
            if col_id and col_vend:
                df_a = df_a.rename(columns={col_id: 'clienteid', col_vend: 'vendedor'})
                df_a['clienteid'] = df_a['clienteid'].astype(str)
                df_a['vendedor'] = df_a['vendedor'].astype(str).str.strip()
                df_a = df_a[['clienteid', 'vendedor']].drop_duplicates(subset=['clienteid'])

    # 3. CARGAR PREVENTA
    if file_preventa:
        df_p = read_smart(file_preventa)
        if df_p is not None and 'fecha' in df_p.columns:
            df_p['fecha'] = pd.to_datetime(df_p['fecha'], format='%d/%m/%Y', dayfirst=True, errors='coerce')
            if 'monto_final' in df_p.columns: df_p['monto_pre'] = df_p['monto_final']
            elif 'monto' in df_p.columns: df_p['monto_pre'] = df_p['monto']
            else: df_p['monto_pre'] = 0
            
            # Id cruce
            col_pre_id = next((c for c in df_p.columns if 'nro' in c and 'preventa' in c), None)
            if col_pre_id: df_p['id_cruce'] = df_p[col_pre_id]

    # --- ENRIQUECIMIENTO ---
    if df_v is not None and df_a is not None:
        # Usar Vendedor del Maestro como prioritario
        df_v = df_v.rename(columns={'vendedor': 'vendedor_venta'}) 
        df_v = pd.merge(df_v, df_a[['clienteid', 'vendedor']], on='clienteid', how='left')
        df_v['vendedor'] = df_v['vendedor'].fillna(df_v['vendedor_venta'])
        
        # Recalcular canal con el vendedor correcto
        df_v['canal'] = df_v['vendedor'].map(cat_map).fillna('6. RUTA TDB')

    return df_v, df_p, df_a

# --- FUNCIÓN FECHA SEGURA ---
def get_max_date_safe(df):
    if df is not None and not df.empty and 'fecha' in df.columns:
        valid = df['fecha'].dropna()
        if not valid.empty: return valid.max().strftime('%d-%m-%Y')
    return "N/A"

# --- INTERFAZ ---
with st.sidebar:
    st.title("💎 Master Dashboard v22.2")
    st.info("Carga Automática Inteligente Activada")
    st.markdown("---")
    meta = st.number_input("Meta Mensual ($)", value=2500000, step=100000)

df_v, df_p, df_a = load_consolidated_data()

if df_v is not None:
    
    # FILTROS
    sel_canal = st.multiselect("Canal:", df_v['canal'].unique(), default=df_v['canal'].unique())
    dff = df_v[df_v['canal'].isin(sel_canal)].copy()
    
    # KPIs
    tot = dff['monto_real'].sum()
    cob = dff['clienteid'].nunique()
    trx = dff['id_transaccion'].nunique()
    
    c1, c2 = st.columns([1, 2])
    with c1:
        fig_gauge = go.Figure(go.Indicator(mode="gauge+number+delta", value=tot, delta={'reference': meta}, gauge={'axis': {'range': [None, meta*1.2]}, 'bar': {'color': "#2C3E50"}, 'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': meta}}))
        fig_gauge.update_layout(height=200, margin=dict(t=30,b=10,l=30,r=30))
        st.plotly_chart(fig_gauge, use_container_width=True)
    with c2:
        k1, k2, k3 = st.columns(3)
        k1.metric("Ventas", f"${tot:,.0f}")
        k2.metric("Cobertura", f"{cob}")
        k3.metric("Tickets", f"{trx}")
        
        # Mensaje de estado de archivos
        status_txt = "✅ Venta OK"
        if df_p is not None: status_txt += " | ✅ Preventa OK"
        else: status_txt += " | ⚠️ Sin Preventa"
        if df_a is not None: status_txt += " | ✅ Maestro OK"
        else: status_txt += " | ⚠️ Sin Maestro"
        st.info(status_txt)

    st.markdown("---")
    
    tabs = st.tabs(["🎯 Penetración", "📉 Caída", "🎮 Simulador", "📈 Estrategia", "💳 Finanzas", "👥 Clientes", "🔍 Auditoría", "🧠 Inteligencia"])
    
    # 1. PENETRACIÓN
    with tabs[0]:
        if df_a is not None:
            st.header("🎯 Penetración de Cartera")
            
            # Filtrar asignaciones solo de los vendedores seleccionados en el filtro de canal
            vendedores_activos = dff['vendedor'].unique()
            df_a_filtered = df_a[df_a['vendedor'].isin(vendedores_activos)]

            asig = df_a_filtered.groupby('vendedor')['clienteid'].nunique().reset_index(name='Asignados')
            serv = dff.groupby('vendedor')['clienteid'].nunique().reset_index(name='Servidos')
            
            pen = pd.merge(asig, serv, on='vendedor', how='left').fillna(0)
            pen['% Pen'] = (pen['Servidos'] / pen['Asignados'].replace(0, 1)) * 100
            pen['Sin Compra'] = pen['Asignados'] - pen['Servidos']
            pen = pen.sort_values('% Pen', ascending=False)
            
            st.dataframe(pen.style.format({'% Pen': '{:.1f}%', 'Asignados': '{:.0f}', 'Servidos': '{:.0f}', 'Sin Compra': '{:.0f}'}), use_container_width=True)
            
            fig_p = go.Figure(data=[
                go.Bar(name='Servidos', y=pen['vendedor'], x=pen['Servidos'], orientation='h', marker_color='#2ECC71'),
                go.Bar(name='Sin Compra', y=pen['vendedor'], x=pen['Sin Compra'], orientation='h', marker_color='#E74C3C')
            ])
            fig_p.update_layout(barmode='stack', title="Cobertura de Cartera", height=500)
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.warning("No se encontró un archivo Maestro válido. Verifica que contenga 'Cliente ID' y 'Vendedor'.")

    # 2. CAÍDA
    with tabs[1]:
        if df_p is not None and not dff.empty:
            st.header("📉 Análisis de Rechazos")
            ven_g = dff.groupby('preventaid')['monto_real'].sum().reset_index()
            pre_g = df_p.groupby('id_cruce')['monto_pre'].sum().reset_index()
            m = pd.merge(pre_g, ven_g, left_on='id_cruce', right_on='preventaid', how='left').fillna(0)
            m['diff'] = m['monto_pre'] - m['monto_real']
            m['estado'] = m.apply(lambda x: 'Entregado' if x['diff'] <= 5 else ('Rechazo Total' if x['monto_real'] < 1 else 'Parcial'), axis=1)
            
            c1, c2 = st.columns(2)
            c1.plotly_chart(px.pie(m, names='estado', values='monto_pre', title="Estado Pedidos ($)"), use_container_width=True)
            
            # Detalle caída por vendedor
            m_det = pd.merge(df_p, ven_g, left_on='id_cruce', right_on='preventaid', how='left').fillna(0)
            m_det['caida'] = m_det['monto_pre'] - m_det['monto_real']
            top_drop = m_det.groupby('vendedor')['caida'].sum().sort_values(ascending=False).head(10).reset_index()
            c2.plotly_chart(px.bar(top_drop, x='caida', y='vendedor', orientation='h', title="$$ Perdidos por Vendedor", color='caida', color_continuous_scale='Reds'), use_container_width=True)
        else: st.warning("Falta archivo de Preventas o datos de cruce.")

    # 3. SIMULADOR
    with tabs[2]:
        st.header("🎮 Simulador")
        if not dff.empty:
            d_left = max(0, 30 - df_v['fecha'].max().day)
            st.info(f"Días restantes: {d_left}")
            c_s1, c_s2 = st.columns([1, 2])
            with c_s1:
                dt = st.slider("Subir Ticket %", 0, 50, 0)
                dc = st.slider("Subir Cobertura %", 0, 50, 0)
            with c_s2:
                d_avg = tot / df_v['fecha'].max().day
                proj = tot + (d_avg * (1+dt/100) * (1+dc/100) * d_left)
                st.metric("Cierre Proyectado", f"${proj:,.0f}", f"{proj-meta:,.0f} vs Meta")
        else: st.warning("Sin datos.")

    # 4. ESTRATEGIA
    with tabs[3]:
        if not dff.empty:
            day = dff.groupby('fecha').agg({'monto_real':'sum', 'clienteid':'nunique'}).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Bar(x=day['fecha'], y=day['monto_real'], name='Venta'))
            fig.add_trace(go.Scatter(x=day['fecha'], y=day['clienteid'], name='Clientes', yaxis='y2', line=dict(color='red', width=3)))
            fig.update_layout(yaxis2=dict(overlaying='y', side='right'), title="Venta vs Clientes", height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            sun = dff.groupby(['canal', 'vendedor'])['monto_real'].sum().reset_index()
            st.plotly_chart(px.sunburst(sun, path=['canal', 'vendedor'], values='monto_real'), use_container_width=True)

    # 5. FINANZAS
    with tabs[4]:
        if not dff.empty:
            pay = dff.groupby('tipopago')['monto_real'].sum().reset_index()
            st.plotly_chart(px.pie(pay, values='monto_real', names='tipopago', title="Mix Pago"), use_container_width=True)

    # 6. CLIENTES
    with tabs[5]:
        if not dff.empty and 'cliente' in dff.columns:
            cl = st.selectbox("Cliente:", sorted(dff['cliente'].unique()))
            if cl:
                cd = dff[dff['cliente']==cl]
                st.metric("Total", f"${cd['monto_real'].sum():,.0f}")
                st.plotly_chart(px.bar(cd.groupby('producto')['monto_real'].sum().nlargest(5).reset_index(), x='monto_real', y='producto', orientation='h'), use_container_width=True)

    # 7. AUDITORIA
    with tabs[6]:
        if not dff.empty:
            cat = 'jerarquia1' if 'jerarquia1' in dff.columns else 'categoria'
            piv = dff.groupby(['vendedor', cat])['monto_real'].sum().reset_index().pivot(index='vendedor', columns=cat, values='monto_real').fillna(0)
            st.plotly_chart(px.imshow(piv, aspect="auto", title="Heatmap Categorías"), use_container_width=True)

    # 8. INTELIGENCIA
    with tabs[7]:
        if not dff.empty:
            p = st.selectbox("Producto Base:", dff.groupby('producto')['monto_real'].sum().nlargest(50).index)
            if p:
                txs = dff[dff['producto']==p]['id_transaccion'].unique()
                rel = dff[dff['id_transaccion'].isin(txs)]
                rel = rel[rel['producto']!=p].groupby('producto')['id_transaccion'].nunique().nlargest(5)
                st.table(rel)

else:
    st.error("⚠️ No se encontraron archivos. Verifica que en GitHub existan: 'venta_completa.csv', 'preventa_completa.csv' y 'maestro_de_clientes.csv'.")
