import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os
from io import StringIO

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Master Sales Command v21.0", page_icon="💎", layout="wide")

# --- ESTILOS CSS (OMITIDOS PARA BREVEDAD) ---

# --- FUNCIÓN DE LECTURA DE ARCHIVOS CONSOLIDADOS DESDE REPOSITORIO ---
@st.cache_data
def load_consolidated_data():
    VENTA_FILE = 'venta_completa.csv'
    PREVENTA_FILE = 'preventa_completa.csv'
    MAESTRO_FILE = 'maestro_de_clientes.csv' # NUEVO: Archivo de asignación
    
    df_v, df_p, df_a = None, None, None
    
    def read_and_clean(file_path):
        try:
            # Leer con ; (por ser archivo maestro)
            df_temp = pd.read_csv(file_path, sep=';', on_bad_lines='skip', encoding='utf-8')
            if df_temp.shape[1] < 5: # Si lee mal, reintentamos con coma
                df_temp = pd.read_csv(file_path, sep=',', on_bad_lines='skip', encoding='utf-8')
            
            df_temp.columns = df_temp.columns.str.strip().str.lower().str.replace(' ', '_')
            return df_temp
        except Exception:
            return None

    # LECTURA DE VENTA
    if os.path.exists(VENTA_FILE):
        df_v_raw = read_and_clean(VENTA_FILE)
        if df_v_raw is not None and 'fecha' in df_v_raw.columns:
            df_v = df_v_raw
            # Limpieza y preparación de columnas de Venta
            df_v['clienteid'] = df_v.get('cliente_id', df_v['clienteid']).astype(str) # Aseguramos el nombre
            df_v['cliente'] = df_v['cliente'].astype(str).str.strip().str.upper()
            df_v['fecha'] = pd.to_datetime(df_v['fecha'], format='%d/%m/%Y', dayfirst=True, errors='coerce')
            df_v['semana_anio'] = df_v['fecha'].dt.isocalendar().week
            
            if 'montofinal' in df_v.columns: df_v['monto_real'] = df_v['montofinal']
            else: df_v['monto_real'] = df_v['monto']
            
            df_v['id_transaccion'] = df_v.get('ventaid', df_v.columns[0])
            
            # Mapeo de Canales (usamos mapeo temporal antes de la fusión con el maestro)
            df_v['canal'] = df_v['vendedor'].map({
                'JOSE CARLOS MENDOZA MENDOZA': '1. MAYORISTAS', 'KEVIN  COLODRO VACA': '1. MAYORISTAS',
                # ... resto del mapeo ...
            }).fillna('6. RUTA TDB')

    # LECTURA DE ASIGNACIONES (MAESTRO DE CLIENTES)
    if os.path.exists(MAESTRO_FILE):
        df_a_raw = read_and_clean(MAESTRO_FILE)
        if df_a_raw is not None and 'cliente_id' in df_a_raw.columns and 'vendedor' in df_a_raw.columns:
            df_a = df_a_raw.copy()
            df_a['cliente_id'] = df_a['cliente_id'].astype(str)
            df_a['vendedor'] = df_a['vendedor'].astype(str).str.strip()
            df_a = df_a[['cliente_id', 'vendedor']].drop_duplicates(subset=['cliente_id']) # Mantener una asignación única

    # LECTURA DE PREVENTA (omisión para brevedad)
    if os.path.exists(PREVENTA_FILE):
        # Lógica de carga de Preventa... (igual que antes)
        pass # Placeholder for actual code (to keep it short)

    # --- ENRIQUECIMIENTO (FUSIÓN MAESTRO + VENTA) ---
    if df_v is not None and df_a is not None:
        # Se fusiona para obtener la lista completa de clientes asignados vs servidos
        df_v = pd.merge(df_v, df_a[['cliente_id', 'vendedor']], on='cliente_id', how='left', suffixes=('_venta', '_maestro'))
        # Usamos el vendedor del Maestro si el de la venta es nulo o queremos consistencia
        df_v['vendedor'] = df_v['vendedor_maestro'].fillna(df_v['vendedor_venta'])


    return df_v, df_p, df_a

# --- INTERFAZ ---
with st.sidebar:
    st.title("💎 Master Dashboard v21.0")
    # ... Resto de la interfaz y Metas ...
    meta = st.number_input("Objetivo Mensual ($)", value=2500000, step=100000)

# Ejecución de carga
df_v, df_p, df_a = load_consolidated_data() # Carga los 3 dataframes

if df_v is not None:
    
    # ... Filtros y KPIs (igual que antes) ...
    dff = df_v # Usamos df_v para simplificar, ya que no hay filtro de canal
    
    # ... Cálculo de KPIs ...

    st.markdown("---")
    
    # --- PESTAÑAS (AÑADIMOS PENETRACIÓN) ---
    tabs = st.tabs(["🎯 Penetración (NUEVO)", "📉 Análisis Caída", "🎮 Simulador", "📈 Estrategia", "💳 Finanzas", "👥 Clientes 360", "🔍 Auditoría", "🧠 Inteligencia"])
    
    # 1. PENETRACIÓN (NUEVO MODULO)
    with tabs[0]:
        if df_a is not None:
            st.header("🎯 Penetración de Cobertura Asignada")
            
            # 1. Clientes Asignados por Vendedor (del Maestro)
            assigned_clients = df_a.groupby('vendedor')['cliente_id'].nunique().reset_index()
            assigned_clients.columns = ['vendedor', 'Asignados']
            
            # 2. Clientes Servidos por Vendedor (de la Venta Real)
            served_clients = dff.groupby('vendedor')['clienteid'].nunique().reset_index()
            served_clients.columns = ['vendedor', 'Servidos']
            
            # 3. Merge y Cálculo
            penetration_df = pd.merge(assigned_clients, served_clients, on='vendedor', how='left').fillna(0)
            
            penetration_df['Penetracion %'] = (penetration_df['Servidos'] / penetration_df['Asignados']) * 100
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
            st.warning("⚠️ Falta el archivo 'maestro_de_clientes.csv' para calcular la Penetración.")

    # ... El resto de las pestañas (Caída, Simulador, Estrategia, etc.) irían aquí usando el nuevo df_v enriquecido ...

    # [Placeholder for the rest of the 7 tabs for the user to copy/paste and merge]

else:
    st.error("🚨 ERROR CRÍTICO: No se pudo cargar el archivo de ventas principal ('venta_completa.csv').")
