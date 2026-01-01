import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="POS De La Tierra", layout="wide")

# --- SEGURIDAD ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔐 Acceso De La Tierra")
    pwd = st.text_input("Clave Maestra:", type="password")
    nombre_e = st.text_input("Nombre del Empleado:")
    if st.button("Entrar"):
        if pwd == "1234" and nombre_e != "":
            st.session_state["autenticado"] = True
            st.session_state["empleado"] = nombre_e
            with open("login_log.txt", "a") as f:
                f.write(f"{datetime.now()}: {nombre_e} entró\n")
            st.rerun()
    st.stop()

# --- CARGA DE DATOS ---
def cargar_datos():
    if not os.path.exists('productos.csv'):
        pd.DataFrame(columns=['Nombre', 'Unidades_Por_Bulk', 'Costo_Por_Bulk', 'Modos']).to_csv('productos.csv', index=False)
    if not os.path.exists('ventas.csv'):
        pd.DataFrame(columns=['Fecha', 'Nombre', 'Modo', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia', 'Empleado']).to_csv('ventas.csv', index=False)
    
    p = pd.read_csv('productos.csv')
    v = pd.read_csv('ventas.csv')
    v['Fecha'] = pd.to_datetime(v['Fecha'])
    return p, v

def guardar_datos(p, v):
    p.to_csv('productos.csv', index=False)
    v.to_csv('ventas.csv', index=False)

productos, ventas = cargar_datos()

# --- MENÚ DE 8 PESTAÑAS ---
st.sidebar.title(f"👤 {st.session_state['empleado']}")
opcion = st.sidebar.selectbox("Menú Principal", [
    "🛒 Registrar Venta", 
    "📋 Inventario Real", 
    "📊 Dashboard", 
    "📅 Registro Mensual",
    "✨ Configurar Productos", 
    "📥 Añadir Stock",
    "✏️ Editar Producto", 
    "⚙️ Gestión (Reset)"
])

# 1. REGISTRAR VENTA
if opcion == "🛒 Registrar Venta":
    st.header("🛒 Terminal de Ventas")
    if productos.empty:
        st.warning("Primero configura un producto en la pestaña ✨")
    else:
        busqueda = st.text_input("🔍 Buscar...")
        df_m = productos[productos['Nombre'].str.contains(busqueda, case=False)] if busqueda else productos
        for idx, p in df_m.iterrows():
            with st.expander(f"📦 {p['Nombre']}"):
                modos = eval(p['Modos'])
                for m_idx, m in enumerate(modos):
                    if st.button(f"Vender {m['nombre']} - C${m['precio']}", key=f"v_{idx}_{m_idx}"):
                        cost_u = p['Costo_Por_Bulk'] / p['Unidades_Por_Bulk']
                        ganancia_v = m['precio'] - (m['unidades'] * cost_u)
                        nv = pd.DataFrame([{'Fecha': datetime.now(), 'Nombre': p['Nombre'], 'Modo': m['nombre'], 'Unidades_Vendidas': m['unidades'], 'Precio_Venta': m['precio'], 'Ganancia': round(ganancia_v, 2), 'Empleado': st.session_state['empleado']}])
                        ventas = pd.concat([ventas, nv], ignore_index=True)
                        guardar_datos(productos, ventas)
                        st.success("¡Venta realizada!")
                        st.rerun()

# 2. INVENTARIO REAL
elif opcion == "📋 Inventario Real":
    st.header("📋 Inventario y Ganancias")
    if not productos.empty:
        res_v = ventas.groupby('Nombre').agg({'Unidades_Vendidas': 'sum', 'Precio_Venta': 'sum', 'Ganancia': 'sum'}).reset_index()
        df_inv = pd.merge(productos, res_v, on='Nombre', how='left').fillna(0)
        df_inv['Stock_Actual'] = df_inv['Unidades_Por_Bulk'] - df_inv['Unidades_Vendidas']
        df_inv['%_Ganancia'] = (df_inv['Ganancia'] / df_inv['Precio_Venta'] * 100).fillna(0).round(1)
        st.table(df_inv[['Nombre', 'Stock_Actual', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia', '%_Ganancia']])
    else: st.info("Inventario vacío.")

# 3. DASHBOARD
elif opcion == "📊 Dashboard":
    st.header("📊 Resumen de Negocio")
    if not ventas.empty:
        col1, col2 = st.columns(2)
        col1.metric("Ingreso Total", f"C$ {ventas['Precio_Venta'].sum():.2f}")
        col2.metric("Ganancia Limpia", f"C$ {ventas['Ganancia'].sum():.2f}")
        st.subheader("Velas de Ganancia por Producto")
        st.bar_chart(ventas.groupby('Nombre')['Ganancia'].sum())
    else: st.info("📊 Las gráficas aparecerán después de la primera venta.")

# 4. REGISTRO MENSUAL
elif opcion == "📅 Registro Mensual":
    st.header("📅 Historial por Mes")
    if not ventas.empty:
        ventas['Mes'] = ventas['Fecha'].dt.strftime('%Y-%m')
        mes = st.selectbox("Mes:", ventas['Mes'].unique())
        st.write(ventas[ventas['Mes'] == mes])
    else: st.info("No hay ventas registradas aún.")

# 5. CONFIGURAR PRODUCTOS
elif opcion == "✨ Configurar Productos":
    st.header("✨ Nuevo Producto")
    with st.form("f1"):
        n = st.text_input("Nombre")
        cb = st.number_input("Costo Bulto", 0.0)
        ub = st.number_input("Unidades en Bulto", 1)
        pv = st.number_input("Precio Venta (Detalle)", 0.0)
        if st.form_submit_button("Guardar"):
            mod = str([{'nombre': 'Detalle', 'unidades': 1, 'precio': pv}])
            new = pd.DataFrame([{'Nombre': n, 'Unidades_Por_Bulk': ub, 'Costo_Por_Bulk': cb, 'Modos': mod}])
            productos = pd.concat([productos, new], ignore_index=True)
            guardar_datos(productos, ventas)
            st.success("Producto creado.")
            st.rerun()

# 6. AÑADIR STOCK
elif opcion == "📥 Añadir Stock":
    st.header("📥 Cargar Mercadería")
    if not productos.empty:
        p_sel = st.selectbox("¿A qué producto?", productos['Nombre'])
        idx = productos[productos['Nombre'] == p_sel].index[0]
        cuanto = st.number_input("Unidades nuevas", 1)
        if st.button("Sumar al Inventario"):
            productos.at[idx, 'Unidades_Por_Bulk'] += cuanto
            guardar_datos(productos, ventas)
            st.success("Stock actualizado.")
    else: st.warning("Crea productos primero.")

# 7. EDITAR PRODUCTO (CORREGIDO - NO MÁS NEGRO)
elif opcion == "✏️ Editar Producto":
    st.header("✏️ Modificar Existentes")
    if not productos.empty:
        p_edit = st.selectbox("Selecciona producto:", productos['Nombre'])
        idx = productos[productos['Nombre'] == p_edit].index[0]
        # Cargamos los valores actuales para que no esté vacío
        nom_act = st.text_input("Nombre:", value=productos.at[idx, 'Nombre'])
        cost_act = st.number_input("Costo Bulto:", value=float(productos.at[idx, 'Costo_Por_Bulk']))
        if st.button("Actualizar"):
            productos.at[idx, 'Nombre'] = nom_act
            productos.at[idx, 'Costo_Por_Bulk'] = cost_act
            guardar_datos(productos, ventas)
            st.success("Cambios aplicados.")
            st.rerun()
    else: st.info("No hay productos para editar.")

# 8. GESTIÓN (RESET)
elif opcion == "⚙️ Gestión (Reset)":
    st.header("⚙️ Limpieza de Sistema")
    if st.button("🚨 BORRAR SOLO VENTAS"):
        guardar_datos(productos, pd.DataFrame(columns=['Fecha', 'Nombre', 'Modo', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia', 'Empleado']))
        st.rerun()
    if st.button("🧨 RESETEAR TODO"):
        if os.path.exists('productos.csv'): os.remove('productos.csv')
        if os.path.exists('ventas.csv'): os.remove('ventas.csv')
        st.rerun()
