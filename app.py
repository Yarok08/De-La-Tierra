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
    st.title("🔐 Acceso al Sistema")
    pwd = st.text_input("Clave Maestra:", type="password")
    nombre_e = st.text_input("Nombre del Empleado:")
    if st.button("Entrar"):
        if pwd == "1234" and nombre_e != "":
            st.session_state["autenticado"] = True
            st.session_state["empleado"] = nombre_e
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

# --- MENÚ COMPLETO (SIN QUITAR NADA) ---
st.sidebar.title(f"👤 {st.session_state['empleado']}")
opcion = st.sidebar.selectbox("Menú", [
    "Registrar Ventas", 
    "Inventario Real", 
    "Configurar Productos", 
    "Añadir Stock",
    "Editar Precios",
    "Dashboard", 
    "Gestión (Reset)"
])

# --- 1. REGISTRAR VENTAS ---
if opcion == "Registrar Ventas":
    st.header("🛒 Ventas")
    busqueda = st.text_input("🔍 Buscar producto...")
    df_m = productos[productos['Nombre'].str.contains(busqueda, case=False)] if busqueda else productos
    
    for idx, p in df_m.iterrows():
        with st.expander(f"📦 {p['Nombre']}"):
            modos = eval(p['Modos'])
            for m_idx, m in enumerate(modos):
                if st.button(f"{m['nombre']} - C${m['precio']}", key=f"v_{idx}_{m_idx}"):
                    cost_u = p['Costo_Por_Bulk'] / p['Unidades_Por_Bulk']
                    ganancia_v = m['precio'] - (m['unidades'] * cost_u)
                    nv = pd.DataFrame([{'Fecha': datetime.now(), 'Nombre': p['Nombre'], 'Modo': m['nombre'], 'Unidades_Vendidas': m['unidades'], 'Precio_Venta': m['precio'], 'Ganancia': round(ganancia_v, 2), 'Empleado': st.session_state['empleado']}])
                    ventas = pd.concat([ventas, nv], ignore_index=True)
                    guardar_datos(productos, ventas)
                    st.success("✅ Venta Guardada")
                    st.rerun()

# --- 2. INVENTARIO REAL ---
elif opcion == "Inventario Real":
    st.header("📋 Control de Stock y Ganancias")
    if not productos.empty:
        res_v = ventas.groupby('Nombre').agg({'Unidades_Vendidas': 'sum', 'Precio_Venta': 'sum', 'Ganancia': 'sum'}).reset_index()
        df_inv = pd.merge(productos, res_v, on='Nombre', how='left').fillna(0)
        df_inv['Stock_Restante'] = df_inv['Unidades_Por_Bulk'] - df_inv['Unidades_Vendidas']
        df_inv['%_Ganancia'] = (df_inv['Ganancia'] / df_inv['Precio_Venta'] * 100).fillna(0).round(2)
        tabla = df_inv[['Nombre', 'Unidades_Por_Bulk', 'Stock_Restante', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia', '%_Ganancia']]
        st.dataframe(tabla, use_container_width=True)
        st.metric("Ganancia Total Acumulada", f"C$ {ventas['Ganancia'].sum():.2f}")
    else:
        st.info("No hay productos.")

# --- 3. CONFIGURAR PRODUCTOS (NUEVOS) ---
elif opcion == "Configurar Productos":
    st.header("🆕 Nuevo Producto")
    with st.form("nuevo_p"):
        nom = st.text_input("Nombre del Producto")
        costo_b = st.number_input("Costo del Bulto (C$)", min_value=0.0)
        cant_b = st.number_input("Total Unidades en el Bulto", min_value=1)
        st.write("---")
        st.write("Define cómo lo vendes (Ej: Detalle, Media Docena, Docena):")
        m1_n = st.text_input("Modo 1 (Nombre)", value="Detalle")
        m1_u = st.number_input("Unidades en Modo 1", value=1)
        m1_p = st.number_input("Precio Modo 1", value=0.0)
        if st.form_submit_button("Guardar Producto"):
            modos_list = [{'nombre': m1_n, 'unidades': m1_u, 'precio': m1_p}]
            nuevo = pd.DataFrame([{'Nombre': nom, 'Unidades_Por_Bulk': cant_b, 'Costo_Por_Bulk': costo_b, 'Modos': str(modos_list)}])
            productos = pd.concat([productos, nuevo], ignore_index=True)
            guardar_datos(productos, ventas)
            st.success("Producto creado")
            st.rerun()

# --- 4. GESTIÓN (RESET PARA TUS PRUEBAS) ---
elif opcion == "Gestión (Reset)":
    st.header("⚙️ Zona de Peligro")
    st.warning("Esto borrará permanentemente los datos seleccionados.")
    if st.button("🚨 BORRAR SOLO VENTAS (Dejar productos)"):
        ventas = pd.DataFrame(columns=['Fecha', 'Nombre', 'Modo', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia', 'Empleado'])
        guardar_datos(productos, ventas)
        st.success("Ventas reseteadas a cero.")
        st.rerun()
    
    if st.button("🧨 BORRAR TODO (Ventas y Productos)"):
        productos = pd.DataFrame(columns=['Nombre', 'Unidades_Por_Bulk', 'Costo_Por_Bulk', 'Modos'])
        ventas = pd.DataFrame(columns=['Fecha', 'Nombre', 'Modo', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia', 'Empleado'])
        guardar_datos(productos, ventas)
        st.success("Sistema totalmente limpio.")
        st.rerun()
