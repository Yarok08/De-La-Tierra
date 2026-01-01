import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go

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

# --- CARGA DE DATOS ---
def cargar_datos():
    if not os.path.exists('productos.csv'):
        pd.DataFrame(columns=['Nombre', 'Unidades_Por_Bulk', 'Costo_Por_Bulk', 'Modos', 'Categoria']).to_csv('productos.csv', index=False)
    if not os.path.exists('ventas.csv'):
        pd.DataFrame(columns=['Fecha', 'Nombre', 'Modo', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia', 'Empleado']).to_csv('ventas.csv', index=False)
    
    p = pd.read_csv('productos.csv')
    v = pd.read_csv('ventas.csv')
    if 'Categoria' not in p.columns: p['Categoria'] = 'General'
    p['Categoria'] = p['Categoria'].fillna('General').astype(str)
    if not v.empty:
        v['Fecha'] = pd.to_datetime(v['Fecha'], errors='coerce')
    return p, v

def guardar_datos(p, v):
    p.to_csv('productos.csv', index=False)
    v.to_csv('ventas.csv', index=False)

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
        except:
            return False, ""
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
                        try: modos = eval(p_row['Modos'])
                        except: modos = []
                        if len(modos) > 0:
                            cols = st.columns(len(modos))
                            for m_idx, m in enumerate(modos):
                                if cols[m_idx].button(f"{m['nombre']}\nC${m['precio']}", key=f"v_{idx}_{m_idx}_{tab_nom}"):
                                    cost_u = p_row['Costo_Por_Bulk'] / p_row['Unidades_Por_Bulk']
                                    ganancia_v = m['precio'] - (m['unidades'] * cost_u)
                                    nv = pd.DataFrame([{'Fecha': datetime.now(), 'Nombre': p_row['Nombre'], 'Modo': m['nombre'], 'Unidades_Vendidas': m['unidades'], 'Precio_Venta': m['precio'], 'Ganancia': round(ganancia_v, 2), 'Empleado': st.session_state['empleado']}])
                                    ventas = pd.concat([ventas, nv], ignore_index=True)
                                    guardar_datos(productos, ventas)
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
        else: st.success("Inventario saludable.")

# 5. REGISTRO MENSUAL
elif opcion == "📅 Registro Mensual":
    st.header("📅 Historial y Cierre Mensual")
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
                st.success(f"Mes {mes_actual} guardado con éxito.")
        else: st.info("No hay ventas este mes.")

    with tab2:
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
        idx = productos[productos['Nombre'] == p_sel].index[0]
        p_data = productos.iloc[idx]
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
                    productos.at[idx, 'Unidades_Por_Bulk'] += u_n
                    productos.at[idx, 'Costo_Por_Bulk'] = round(ponderado_proy * productos.at[idx, 'Unidades_Por_Bulk'], 2)
                    guardar_datos(productos, ventas)
                    st.success("¡Stock y Costo Ponderado actualizados!")
                    st.rerun()
                else: st.error("Ingrese unidades válidas.")

# 8. EDITAR PRODUCTO (BOTÓN DE ELIMINAR RE-AÑADIDO)
elif opcion == "✏️ Editar Producto":
    st.header("✏️ Editar Datos del Producto")
    if not productos.empty:
        p_edit = st.selectbox("Producto:", productos['Nombre'])
        idx = productos[productos['Nombre'] == p_edit].index[0]
        p_data = productos.iloc[idx]
        with st.form("edit_basic"):
            new_n = st.text_input("Nombre:", value=p_data['Nombre'])
            new_cat = st.text_input("Categoría:", value=p_data['Categoria'])
            modos_act = eval(p_data['Modos'])
            nuevos_modos = []
            for i in range(5):
                m_n_v = modos_act[i]['nombre'] if i < len(modos_act) else ""
                m_u_v = modos_act[i]['unidades'] if i < len(modos_act) else 1
                m_p_v = modos_act[i]['precio'] if i < len(modos_act) else 0.0
                c1, c2, c3 = st.columns(3)
                m_n = c1.text_input(f"Modo {i+1}", value=m_n_v, key=f"en_{i}")
                m_u = c2.number_input(f"Unid {i+1}", min_value=1, value=int(m_u_v), key=f"eu_{i}")
                m_p = c3.number_input(f"Precio {i+1}", value=float(m_p_v), key=f"ep_{i}")
                if m_n: nuevos_modos.append({'nombre': m_n, 'unidades': m_u, 'precio': m_p})
            if st.form_submit_button("Guardar Cambios"):
                productos.at[idx, 'Nombre'] = new_n
                productos.at[idx, 'Categoria'] = new_cat
                productos.at[idx, 'Modos'] = str(nuevos_modos)
                guardar_datos(productos, ventas)
                st.rerun()
        
        # Botón de eliminar fuera del formulario para mayor seguridad
        st.markdown("---")
        if st.button(f"🗑️ ELIMINAR COMPLETAMENTE '{p_edit}'"):
            productos = productos.drop(idx)
            guardar_datos(productos, ventas)
            st.success(f"Producto {p_edit} eliminado.")
            st.rerun()

# 6. CONFIGURAR PRODUCTOS
elif opcion == "✨ Configurar Productos":
    st.header("✨ Nuevo Producto")
    with st.form("f_conf"):
        n = st.text_input("Nombre")
        cat = st.text_input("Categoría", "General")
        cb = st.number_input("Costo Bulto", 0.0)
        ub = st.number_input("Unidades Bulto", 1)
        modos = []
        for i in range(5):
            c1, c2, c3 = st.columns(3)
            m_n = c1.text_input(f"Etiqueta {i+1}", key=f"cn_{i}")
            m_u = c2.number_input(f"Unid {i+1}", min_value=1, key=f"cu_{i}")
            m_p = c3.number_input(f"Precio {i+1}", key=f"cp_{i}")
            if m_n: modos.append({'nombre': m_n, 'unidades': m_u, 'precio': m_p})
        if st.form_submit_button("Guardar"):
            new = pd.DataFrame([{'Nombre': n, 'Categoria': cat, 'Costo_Por_Bulk': cb, 'Unidades_Por_Bulk': ub, 'Modos': str(modos)}])
            productos = pd.concat([productos, new], ignore_index=True)
            guardar_datos(productos, ventas)
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
        guardar_datos(productos, pd.DataFrame(columns=['Fecha', 'Nombre', 'Modo', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia', 'Empleado']))
        st.rerun()
    if st.button("🧨 RESET TOTAL"):
        if os.path.exists('productos.csv'): os.remove('productos.csv')
        if os.path.exists('ventas.csv'): os.remove('ventas.csv')
        if os.path.exists('sesion.vix'): os.remove('sesion.vix')
        st.rerun()
