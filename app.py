import streamlit as st
import pandas as pd
import os
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE NUBE (SUPABASE) ---
URL_BASE = "https://asyctjpmxkuznsvxezlo.supabase.co/rest/v1"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFzeWN0anBteGt1em5zdnhlemxvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjcyOTk3OTEsImV4cCI6MjA4Mjg3NTc5MX0.M10bUWziz5MMGm-uDqIBB31WFcVS87ar5gBoC5PT70M"

HEADERS = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="POS De La Tierra", layout="wide")

# --- EFECTOS ---
def efecto_confirmacion_venta():
    efecto_html = """
        <div style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background-color: rgba(46, 204, 113, 0.4); z-index: 9999; pointer-events: none;
            animation: flash_animation 0.6s ease-out forwards;"></div>
        <style> @keyframes flash_animation { 0% { opacity: 1; } 100% { opacity: 0; } } </style>
    """
    st.components.v1.html(efecto_html, height=0)

# --- CARGA DE DATOS (NUBE) ---
def cargar_datos():
    try:
        # Productos
        res_p = requests.get(f"{URL_BASE}/productos?select=*", headers=HEADERS)
        p_raw = pd.DataFrame(res_p.json()) if res_p.status_code == 200 else pd.DataFrame()
        if not p_raw.empty:
            p = p_raw.rename(columns={'nombre': 'Nombre', 'unidades_por_bulk': 'Unidades_Por_Bulk', 'costo_por_bulk': 'Costo_Por_Bulk', 'modos': 'Modos', 'categoria': 'Categoria'})
        else:
            p = pd.DataFrame(columns=['Nombre', 'Unidades_Por_Bulk', 'Costo_Por_Bulk', 'Modos', 'Categoria'])

        # Ventas
        res_v = requests.get(f"{URL_BASE}/ventas?select=*", headers=HEADERS)
        v_raw = pd.DataFrame(res_v.json()) if res_v.status_code == 200 else pd.DataFrame()
        if not v_raw.empty:
            v = v_raw.rename(columns={'fecha': 'Fecha', 'nombre_producto': 'Nombre', 'modo': 'Modo', 'unidades_vendidas': 'Unidades_Vendidas', 'precio_venta': 'Precio_Venta', 'ganancia': 'Ganancia', 'empleado': 'Empleado'})
            v['Fecha'] = pd.to_datetime(v['Fecha'], errors='coerce')
        else:
            v = pd.DataFrame(columns=['Fecha', 'Nombre', 'Modo', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia', 'Empleado'])
        
        # Asegurar tipos
        p['Categoria'] = p['Categoria'].fillna('General').astype(str)
        return p, v
    except:
        return pd.DataFrame(columns=['Nombre', 'Unidades_Por_Bulk', 'Costo_Por_Bulk', 'Modos', 'Categoria']), pd.DataFrame(columns=['Fecha', 'Nombre', 'Modo', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia', 'Empleado'])

# Wrapper para mantener compatibilidad
def guardar_datos(p, v):
    pass

productos, ventas = cargar_datos()

# --- LÓGICA DE SESIÓN PERSISTENTE ---
def verificar_sesion_persistente():
    if os.path.exists('sesion.vix'):
        try:
            with open('sesion.vix', 'r') as f:
                datos = f.read().split('|')
                fecha_login = datetime.strptime(datos[0], '%Y-%m-%d %H:%M:%S')
                nombre_e = datos[1]
                if datetime.now() < fecha_login + timedelta(hours=24):
                    return True, nombre_e
        except: return False, ""
    return False, ""

def guardar_sesion_local(nombre):
    with open('sesion.vix', 'w') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}|{nombre}")

# --- SEGURIDAD ---
if "autenticado" not in st.session_state:
    valido, nombre_guardado = verificar_sesion_persistente()
    if valido:
        st.session_state["autenticado"] = True
        st.session_state["empleado"] = nombre_guardado
    else:
        st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔐 Acceso De La Tierra")
    pwd = st.text_input("Clave Maestra:", type="password")
    nombre_e = st.text_input("Nombre del Empleado:")
    if st.button("Entrar"):
        if pwd == "1234" and nombre_e != "":
            st.session_state["autenticado"] = True
            st.session_state["empleado"] = nombre_e
            guardar_sesion_local(nombre_e)
            st.rerun()
    st.stop()

# --- MENÚ ---
opcion = st.sidebar.selectbox("Menú Principal", [
    "🛒 Registrar Venta", "📋 Inventario Real", "📊 Dashboard", 
    "⚠️ Alertas de Stock", "📅 Registro Mensual", "✨ Configurar Productos", 
    "📥 Añadir Stock", "✏️ Editar Producto", "⚙️ Gestión (Reset)"
])

# 1. REGISTRAR VENTA
if opcion == "🛒 Registrar Venta":
    st.header("🛒 Terminal de Ventas")
    if productos.empty:
        st.warning("Configura productos en ✨")
    else:
        lista_cats = sorted(productos['Categoria'].unique().tolist())
        tabs = st.tabs(["Todos"] + lista_cats)
        busqueda = st.text_input("🔍 Buscar...")
        for i, tab_nom in enumerate(["Todos"] + lista_cats):
            with tabs[i]:
                df_f = productos if tab_nom == "Todos" else productos[productos['Categoria'] == tab_nom]
                if busqueda: df_f = df_f[df_f['Nombre'].str.contains(busqueda, case=False)]
                for idx, p_row in df_f.iterrows():
                    with st.expander(f"📦 {p_row['Nombre']}"):
                        try: modos = eval(str(p_row['Modos']))
                        except: modos = []
                        if len(modos) > 0:
                            cols = st.columns(len(modos))
                            for m_idx, m in enumerate(modos):
                                if cols[m_idx].button(f"{m['nombre']}\nC${m['precio']}", key=f"v_{idx}_{m_idx}_{tab_nom}"):
                                    cost_u = p_row['Costo_Por_Bulk'] / p_row['Unidades_Por_Bulk']
                                    ganancia_v = m['precio'] - (m['unidades'] * cost_u)
                                    nv = {
                                        'nombre_producto': p_row['Nombre'], 
                                        'modo': m['nombre'], 
                                        'unidades_vendidas': int(m['unidades']), 
                                        'precio_venta': float(m['precio']), 
                                        'ganancia': round(float(ganancia_v), 2), 
                                        'empleado': st.session_state['empleado']
                                    }
                                    requests.post(f"{URL_BASE}/ventas", headers=HEADERS, json=nv)
                                    efecto_confirmacion_venta()
                                    st.rerun()

# 2. INVENTARIO REAL
elif opcion == "📋 Inventario Real":
    st.header("📋 Inventario Actual")
    if not productos.empty:
        res_v = ventas.groupby('Nombre').agg({'Unidades_Vendidas': 'sum', 'Precio_Venta': 'sum', 'Ganancia': 'sum'}).reset_index() if not ventas.empty else pd.DataFrame(columns=['Nombre','Unidades_Vendidas','Precio_Venta','Ganancia'])
        df_inv = pd.merge(productos, res_v, on='Nombre', how='left').fillna(0)
        df_inv['Stock_Actual'] = df_inv['Unidades_Por_Bulk'] - df_inv['Unidades_Vendidas']
        st.table(df_inv[['Nombre', 'Categoria', 'Stock_Actual', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia']])

# 3. DASHBOARD
elif opcion == "📊 Dashboard":
    st.header("📊 Dashboard Financiero")
    if not ventas.empty:
        c1, c2, c3 = st.columns(3)
        v_total = ventas['Precio_Venta'].sum()
        g_total = ventas['Ganancia'].sum()
        c1.metric("💰 Ventas Totales", f"C$ {v_total:,.2f}")
        c2.metric("📈 Ganancia Total", f"C$ {g_total:,.2f}")
        c3.metric("🛒 Operaciones", len(ventas))
        
        resumen = ventas.groupby('Nombre')['Ganancia'].sum().reset_index()
        colores = ['#27ae60' if x > resumen['Ganancia'].mean() else '#e74c3c' for x in resumen['Ganancia']]
        fig = go.Figure(data=[go.Bar(x=resumen['Nombre'], y=resumen['Ganancia'], marker_color=colores)])
        st.plotly_chart(fig, use_container_width=True)

# 4. ALERTAS DE STOCK (45%)
elif opcion == "⚠️ Alertas de Stock":
    st.header("⚠️ Alertas de Inventario (45%)")
    if not productos.empty:
        res_v = ventas.groupby('Nombre')['Unidades_Vendidas'].sum().reset_index() if not ventas.empty else pd.DataFrame(columns=['Nombre','Unidades_Vendidas'])
        df_alert = pd.merge(productos, res_v, on='Nombre', how='left').fillna(0)
        df_alert['Stock_Actual'] = df_alert['Unidades_Por_Bulk'] - df_alert['Unidades_Vendidas']
        df_alert['Porcentaje'] = (df_alert['Stock_Actual'] / df_alert['Unidades_Por_Bulk']) * 100
        criticos = df_alert[df_alert['Porcentaje'] <= 45]
        if not criticos.empty:
            for _, r in criticos.iterrows():
                st.warning(f"**{r['Nombre']}** al {r['Porcentaje']:.1f}%")
                st.progress(max(0.0, min(float(r['Porcentaje']/100), 1.0)))
        else: 
            st.success("Inventario saludable.") # <--- REPARADO: Leyenda verde devuelta

# 5. REGISTRO MENSUAL
elif opcion == "📅 Registro Mensual":
    st.header("📅 Historial y Cierre Mensual")
    # Busca archivos locales para mantener tu función de históricos
    archivos = [f for f in os.listdir() if f.startswith('ventas_') and f.endswith('.csv')]
    tab1, tab2 = st.tabs(["Mes Actual", "Históricos Guardados"])
    
    with tab1:
        if not ventas.empty:
            ventas['Mes_Ref'] = ventas['Fecha'].dt.strftime('%Y-%m')
            mes_actual = datetime.now().strftime('%Y-%m')
            df_mes = ventas[ventas['Mes_Ref'] == mes_actual]
            st.subheader(f"Resumen de {mes_actual}")
            col1, col2 = st.columns(2)
            col1.metric("Ventas Mes", f"C$ {df_mes['Precio_Venta'].sum():,.2f}")
            col2.metric("Ganancia Mes", f"C$ {df_mes['Ganancia'].sum():,.2f}")
            st.dataframe(df_mes, use_container_width=True)
            if st.button("💾 Archivar y Cerrar Mes"):
                df_mes.to_csv(f"ventas_{mes_actual}.csv", index=False)
                st.success(f"Mes {mes_actual} guardado localmente.")
        else: st.info("No hay ventas este mes.")

    with tab2: # <--- REPARADO: Función de históricos devuelta
        if archivos:
            archivo_sel = st.selectbox("Seleccione un mes pasado:", archivos)
            df_hist = pd.read_csv(archivo_sel)
            st.subheader(f"Análisis de {archivo_sel}")
            c_h1, c_h2 = st.columns(2)
            c_h1.metric("Total Ventas", f"C$ {df_hist['Precio_Venta'].sum():,.2f}")
            c_h2.metric("Total Ganancia", f"C$ {df_hist['Ganancia'].sum():,.2f}")
            res_h = df_hist.groupby('Nombre')['Ganancia'].sum().reset_index()
            fig_h = go.Figure(data=[go.Bar(x=res_h['Nombre'], y=res_h['Ganancia'], marker_color='#3498db')])
            st.plotly_chart(fig_h, use_container_width=True)
            st.dataframe(df_hist)
        else: st.info("No hay archivos históricos todavía.")

# 7. AÑADIR STOCK
elif opcion == "📥 Añadir Stock":
    st.header("📥 Añadir Stock con Costo Ponderado")
    if not productos.empty:
        p_sel = st.selectbox("Producto:", productos['Nombre'])
        p_data = productos[productos['Nombre'] == p_sel].iloc[0]
        
        # Obtener ID de Supabase para actualizar
        res_id = requests.get(f"{URL_BASE}/productos?nombre=eq.{p_sel}&select=id", headers=HEADERS).json()
        db_id = res_id[0]['id']

        v_tot_v = ventas[ventas['Nombre'] == p_sel]['Unidades_Vendidas'].sum() if not ventas.empty else 0
        unidades_en_estante = p_data['Unidades_Por_Bulk'] - v_tot_v
        costo_u_actual = p_data['Costo_Por_Bulk'] / p_data['Unidades_Por_Bulk'] if p_data['Unidades_Por_Bulk'] > 0 else 0
        valor_inv_actual = unidades_en_estante * costo_u_actual

        with st.form("form_ponderado_stock"):
            st.info(f"Inventario actual: {unidades_en_estante} und. | Costo unitario actual: C$ {costo_u_actual:.2f}")
            col1, col2, col3 = st.columns(3)
            u_n = col1.number_input("Unidades nuevas:", min_value=0, value=0)
            c_n = col2.number_input("Costo compra nueva (C$):", min_value=0.0, value=0.0)
            total_u_proy = unidades_en_estante + u_n
            total_v_proy = valor_inv_actual + c_n
            ponderado_proy = total_v_proy / total_u_proy if total_u_proy > 0 else costo_u_actual
            col3.metric("Nuevo Costo Unitario", f"C$ {ponderado_proy:.2f}")
            
            if st.form_submit_button("🚀 Actualizar Stock y Costo"):
                if u_n > 0:
                    nueva_u_total = p_data['Unidades_Por_Bulk'] + u_n
                    nuevo_costo_bulk = round(ponderado_proy * nueva_u_total, 2)
                    payload = {"unidades_por_bulk": int(nueva_u_total), "costo_por_bulk": float(nuevo_costo_bulk)}
                    requests.patch(f"{URL_BASE}/productos?id=eq.{db_id}", headers=HEADERS, json=payload)
                    st.success("¡Stock y Costo Ponderado actualizados en la nube!")
                    st.rerun()
                else: st.error("Ingrese unidades válidas.")

# 8. EDITAR PRODUCTO
elif opcion == "✏️ Editar Producto": # <--- REPARADO: Interfaz completa de 5 modos devuelta
    st.header("✏️ Editar Datos del Producto")
    if not productos.empty:
        p_edit = st.selectbox("Producto:", productos['Nombre'])
        p_data = productos[productos['Nombre'] == p_edit].iloc[0]
        
        res_id = requests.get(f"{URL_BASE}/productos?nombre=eq.{p_edit}&select=id", headers=HEADERS).json()
        db_id = res_id[0]['id']

        with st.form("edit_basic"):
            new_n = st.text_input("Nombre:", value=p_data['Nombre'])
            new_cat = st.text_input("Categoría:", value=p_data['Categoria'])
            try: modos_act = eval(str(p_data['Modos']))
            except: modos_act = []
            
            nuevos_modos = []
            for i in range(5): # <--- REPARADO: Los 5 modos están aquí
                m_n_v = modos_act[i]['nombre'] if i < len(modos_act) else ""
                m_u_v = modos_act[i]['unidades'] if i < len(modos_act) else 1
                m_p_v = modos_act[i]['precio'] if i < len(modos_act) else 0.0
                c1, c2, c3 = st.columns(3)
                m_n = c1.text_input(f"Modo {i+1}", value=m_n_v, key=f"en_{i}")
                m_u = c2.number_input(f"Unid {i+1}", min_value=1, value=int(m_u_v), key=f"eu_{i}")
                m_p = c3.number_input(f"Precio {i+1}", value=float(m_p_v), key=f"ep_{i}")
                if m_n: nuevos_modos.append({'nombre': m_n, 'unidades': m_u, 'precio': m_p})
            
            if st.form_submit_button("Guardar Cambios"):
                payload = {"nombre": new_n, "categoria": new_cat, "modos": str(nuevos_modos)}
                requests.patch(f"{URL_BASE}/productos?id=eq.{db_id}", headers=HEADERS, json=payload)
                st.rerun()
        
        st.markdown("---")
        if st.button(f"🗑️ ELIMINAR COMPLETAMENTE '{p_edit}'"): # <--- REPARADO: Botón de eliminar devuelto
            requests.delete(f"{URL_BASE}/productos?id=eq.{db_id}", headers=HEADERS)
            st.success(f"Producto {p_edit} eliminado de la nube.")
            st.rerun()

# 6. CONFIGURAR PRODUCTOS
elif opcion == "✨ Configurar Productos":
    st.header("✨ Nuevo Producto")
    with st.form("f_conf"):
        n = st.text_input("Nombre")
        cat = st.text_input("Categoría", "General")
        cb = st.number_input("Costo Bulto", 0.0)
        ub = st.number_input("Unidades Bulto", 1)
        modos_config = []
        for i in range(5):
            c1, c2, c3 = st.columns(3)
            m_n = c1.text_input(f"Etiqueta {i+1}", key=f"cn_{i}")
            m_u = c2.number_input(f"Unid {i+1}", min_value=1, key=f"cu_{i}")
            m_p = c3.number_input(f"Precio {i+1}", key=f"cp_{i}")
            if m_n: modos_config.append({'nombre': m_n, 'unidades': m_u, 'precio': m_p})
        if st.form_submit_button("Guardar"):
            new_p = {
                "nombre": n, 
                "categoria": cat, 
                "costo_por_bulk": float(cb), 
                "unidades_por_bulk": int(ub), 
                "modos": str(modos_config)
            }
            requests.post(f"{URL_BASE}/productos", headers=HEADERS, json=new_p)
            st.success("Producto guardado en la nube.")
            st.rerun()

# 9. GESTIÓN
elif opcion == "⚙️ Gestión (Reset)":
    st.header("⚙️ Gestión")
    if st.button("🚪 CERRAR SESIÓN (Salir ahora)"):
        if os.path.exists('sesion.vix'): os.remove('sesion.vix')
        st.session_state["autenticado"] = False
        st.rerun()
    st.markdown("---")
    if st.button("🚨 BORRAR TODAS LAS VENTAS"):
        requests.delete(f"{URL_BASE}/ventas?id=not.is.null", headers=HEADERS)
        st.success("Ventas borradas de la nube.")
        st.rerun()
    if st.button("🧨 RESET TOTAL"):
        requests.delete(f"{URL_BASE}/ventas?id=not.is.null", headers=HEADERS)
        requests.delete(f"{URL_BASE}/productos?id=not.is.null", headers=HEADERS)
        if os.path.exists('sesion.vix'): os.remove('sesion.vix')
        st.success("Sistema reiniciado completamente.")
        st.rerun()
