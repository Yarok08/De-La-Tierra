import streamlit as st
import pandas as pd
import os
from datetime import datetime
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="POS Atómico Pro", layout="wide")

# --- 1. SEGURIDAD Y CONTROL DE EMPLEADO ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔐 Acceso al Sistema")
    pwd = st.text_input("Clave Maestra:", type="password")
    nombre_e = st.text_input("Tu Nombre (Empleado):")
    if st.button("Entrar al Sistema"):
        if pwd == "1234" and nombre_e != "":
            st.session_state["autenticado"] = True
            st.session_state["empleado"] = nombre_e
            st.rerun()
        else: st.error("Clave correcta y nombre son obligatorios.")
    st.stop()

# --- 2. CARGA DE DATOS ---
def cargar_datos():
    if not os.path.exists('productos.csv'):
        pd.DataFrame(columns=['Nombre', 'Unidades_Por_Bulk', 'Costo_Por_Bulk', 'Modos']).to_csv('productos.csv', index=False)
    if not os.path.exists('inventario.csv'):
        pd.DataFrame(columns=['Nombre', 'Stock_Unidades', 'Inversion_Acumulada']).to_csv('inventario.csv', index=False)
    if not os.path.exists('ventas.csv'):
        pd.DataFrame(columns=['Fecha', 'Nombre', 'Modo', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia', 'Empleado']).to_csv('ventas.csv', index=False)
    p = pd.read_csv('productos.csv')
    i = pd.read_csv('inventario.csv')
    v = pd.read_csv('ventas.csv')
    v['Fecha'] = pd.to_datetime(v['Fecha'])
    return p, i, v

def guardar_datos(p, i, v):
    p.to_csv('productos.csv', index=False)
    i.to_csv('inventario.csv', index=False)
    v.to_csv('ventas.csv', index=False)

productos, inventario, ventas = cargar_datos()

# --- 3. MENÚ LATERAL ---
st.sidebar.title(f"👤 {st.session_state['empleado']}")
opcion = st.sidebar.selectbox("Menú", [
    "Registrar Ventas", "Dashboard", "Análisis Mensual", 
    "Ver Inventario", "Añadir al Stock", "Configurar Productos", 
    "Editar Productos", "Gestión (Reset)"
])

# --- 4. REGISTRAR VENTAS ---
if opcion == "Registrar Ventas":
    st.header("🛒 Terminal de Ventas")
    busqueda = st.text_input("🔍 Buscar producto...")
    df_m = productos[productos['Nombre'].str.contains(busqueda, case=False)] if busqueda else productos
    
    cols = st.columns(3)
    for idx, p in df_m.iterrows():
        with cols[idx % 3]:
            with st.expander(f"📦 {p['Nombre']}"):
                modos = eval(p['Modos'])
                for m_idx, m in enumerate(modos):
                    if st.button(f"{m['nombre']} - C${m['precio']}", key=f"v_{idx}_{m_idx}"):
                        cost_u = p['Costo_Por_Bulk'] / p['Unidades_Por_Bulk']
                        ganancia = m['precio'] - (m['unidades'] * cost_u)
                        nv = pd.DataFrame([{'Fecha': datetime.now(), 'Nombre': p['Nombre'], 'Modo': m['nombre'], 'Unidades_Vendidas': m['unidades'], 'Precio_Venta': m['precio'], 'Ganancia': round(ganancia), 'Empleado': st.session_state['empleado']}])
                        ventas = pd.concat([ventas, nv], ignore_index=True)
                        inventario.loc[inventario['Nombre'] == p['Nombre'], 'Stock_Unidades'] -= m['unidades']
                        guardar_datos(productos, inventario, ventas)
                        st.success("✅ ¡Venta Registrada!")
                        st.balloons()
                        time.sleep(0.5)
                        st.rerun()

# --- 5. DASHBOARD (VELAS ROJAS Y VERDES) ---
elif opcion == "Dashboard":
    st.header("📈 Dashboard de Rendimiento")
    if not ventas.empty:
        resumen = ventas.groupby('Nombre')['Precio_Venta'].sum().reset_index()
        promedio = resumen['Precio_Venta'].mean()
        # Lógica de colores: Verde si supera el promedio, Rojo si está por debajo
        resumen['Venta Alta (Verde)'] = resumen['Precio_Venta'].where(resumen['Precio_Venta'] >= promedio, 0)
        resumen['Venta Baja (Rojo)'] = resumen['Precio_Venta'].where(resumen['Precio_Venta'] < promedio, 0)
        
        st.bar_chart(resumen.set_index('Nombre')[['Venta Alta (Verde)', 'Venta Baja (Rojo)']], color=["#00CC96", "#FF4B4B"])
        st.info(f"💡 El promedio de ventas actual es de C$ {round(promedio, 2)}")
    else: st.info("Sin datos.")

# --- 6. EDITAR PRODUCTOS (RESTAURADO) ---
elif opcion == "Editar Productos":
    st.header("📝 Editar Producto Existente")
    p_editar = st.selectbox("Selecciona el producto a modificar:", productos['Nombre'])
    idx = productos[productos['Nombre'] == p_editar].index[0]
    
    with st.form("edit_form"):
        nuevo_nombre = st.text_input("Nombre del Producto", value=productos.at[idx, 'Nombre'])
        c1, c2 = st.columns(2)
        nuevo_u_b = c1.number_input("Unid. por Bulto", value=int(productos.at[idx, 'Unidades_Por_Bulk']))
        nuevo_c_b = c2.number_input("Costo por Bulto", value=int(productos.at[idx, 'Costo_Por_Bulk']))
        
        st.write("--- 💰 Editar Modos de Venta ---")
        modos_actuales = eval(productos.at[idx, 'Modos'])
        nuevos_modos = []
        for i in range(5):
            r1, r2, r3 = st.columns(3)
            # Pre-llenar si el modo existe
            m_n_val = modos_actuales[i]['nombre'] if i < len(modos_actuales) else ""
            m_u_val = modos_actuales[i]['unidades'] if i < len(modos_actuales) else 0
            m_p_val = modos_actuales[i]['precio'] if i < len(modos_actuales) else 0
            
            m_n = r1.text_input(f"Modo {i+1}", value=m_n_val, key=f"en{i}")
            m_u = r2.number_input(f"Unid {i+1}", value=m_u_val, key=f"eu{i}")
            m_p = r3.number_input(f"Precio {i+1}", value=m_p_val, key=f"ep{i}")
            if m_n and m_u > 0: nuevos_modos.append({"nombre": m_n, "unidades": m_u, "precio": m_p})
            
        if st.form_submit_button("ACTUALIZAR PRODUCTO"):
            productos.at[idx, 'Nombre'] = nuevo_nombre
            productos.at[idx, 'Unidades_Por_Bulk'] = nuevo_u_b
            productos.at[idx, 'Costo_Por_Bulk'] = nuevo_c_b
            productos.at[idx, 'Modos'] = str(nuevos_modos)
            guardar_datos(productos, inventario, ventas)
            st.success("✅ Cambios guardados correctamente.")
            st.rerun()

# --- LAS DEMÁS SECCIONES (ANÁLISIS, INVENTARIO, RESET) SE MANTIENEN ---
elif opcion == "Análisis Mensual":
    st.header("🔬 Historial Mensual")
    if not ventas.empty:
        ventas['Mes_Año'] = ventas['Fecha'].dt.to_period('M').astype(str)
        mes_sel = st.selectbox("Selecciona Mes:", sorted(ventas['Mes_Año'].unique(), reverse=True))
        df_mes = ventas[ventas['Mes_Año'] == mes_sel]
        st.metric("Total Mes", f"C$ {df_mes['Precio_Venta'].sum()}")
        st.dataframe(df_mes)

elif opcion == "Gestión (Reset)":
    st.header("⚙️ Gestión")
    if st.button("BORRAR VENTAS"):
        ventas = pd.DataFrame(columns=['Fecha', 'Nombre', 'Modo', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia', 'Empleado'])
        guardar_datos(productos, inventario, ventas)
        st.rerun()

elif opcion == "Ver Inventario":
    st.dataframe(inventario)

elif opcion == "Añadir al Stock":
    p_sel = st.selectbox("Producto:", productos['Nombre'])
    bultos = st.number_input("Bultos:", min_value=1)
    if st.button("Añadir"):
        p_i = productos[productos['Nombre'] == p_sel].iloc[0]
        inventario.loc[inventario['Nombre'] == p_sel, 'Stock_Unidades'] += (bultos * p_i['Unidades_Por_Bulk'])
        guardar_datos(productos, inventario, ventas)
        st.success("Stock actualizado.")

elif opcion == "Configurar Productos":
    with st.form("nuevo"):
        n = st.text_input("Nombre")
        u = st.number_input("Unid. por Bulto", value=240)
        c = st.number_input("Costo Bulto", value=1000)
        modos = []
        for i in range(5):
            r1, r2, r3 = st.columns(3)
            mn = r1.text_input(f"Modo {i+1}", key=f"n{i}")
            mu = r2.number_input(f"Cant {i+1}", key=f"u{i}")
            mp = r3.number_input(f"Precio {i+1}", key=f"p{i}")
            if mn and mu > 0: modos.append({"nombre": mn, "unidades": mu, "precio": mp})
        if st.form_submit_button("Guardar"):
            new = pd.DataFrame([{'Nombre': n, 'Unidades_Por_Bulk': u, 'Costo_Por_Bulk': c, 'Modos': str(modos)}])
            productos = pd.concat([productos, new], ignore_index=True)
            if n not in inventario['Nombre'].values:
                inventario = pd.concat([inventario, pd.DataFrame([{'Nombre': n, 'Stock_Unidades': 0, 'Inversion_Acumulada': 0}])], ignore_index=True)
            guardar_datos(productos, inventario, ventas)
            st.success("Guardado.")