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

# --- MENÚ ---
st.sidebar.title(f"👤 {st.session_state['empleado']}")
opcion = st.sidebar.selectbox("Menú", ["Registrar Ventas", "Inventario Real", "Dashboard", "Editar Productos"])

# --- VISTA DE VENTAS ---
if opcion == "Registrar Ventas":
    st.header("🛒 Ventas")
    busqueda = st.text_input("🔍 Buscar producto...")
    df_m = productos[productos['Nombre'].str.contains(busqueda, case=False)] if busqueda else productos
    
    for idx, p in df_m.iterrows():
        with st.expander(f"📦 {p['Nombre']}"):
            modos = eval(p['Modos'])
            for m_idx, m in enumerate(modos):
                if st.button(f"{m['nombre']} - C${m['precio']}", key=f"v_{idx}_{m_idx}"):
                    # Cálculo de ganancia basado en el costo por unidad
                    cost_u = p['Costo_Por_Bulk'] / p['Unidades_Por_Bulk']
                    ganancia_v = m['precio'] - (m['unidades'] * cost_u)
                    
                    nv = pd.DataFrame([{'Fecha': datetime.now(), 'Nombre': p['Nombre'], 'Modo': m['nombre'], 'Unidades_Vendidas': m['unidades'], 'Precio_Venta': m['precio'], 'Ganancia': round(ganancia_v, 2), 'Empleado': st.session_state['empleado']}])
                    ventas = pd.concat([ventas, nv], ignore_index=True)
                    guardar_datos(productos, ventas)
                    st.success("✅ Venta Guardada")
                    st.rerun()

# --- INVENTARIO REAL (LA PARTE QUE TE FALTABA) ---
elif opcion == "Inventario Real":
    st.header("📋 Control de Stock y Ganancias Reales")
    
    if not productos.empty:
        # Sumamos las ventas por cada producto
        res_v = ventas.groupby('Nombre').agg({'Unidades_Vendidas': 'sum', 'Precio_Venta': 'sum', 'Ganancia': 'sum'}).reset_index()
        
        # Unimos con los productos
        df_inv = pd.merge(productos, res_v, on='Nombre', how='left').fillna(0)
        
        # CÁLCULOS MÁGICOS
        df_inv['Stock_Restante'] = df_inv['Unidades_Por_Bulk'] - df_inv['Unidades_Vendidas']
        df_inv['%_Ganancia'] = (df_inv['Ganancia'] / df_inv['Precio_Venta'] * 100).fillna(0).round(2)
        
        # Tabla final limpia
        tabla = df_inv[['Nombre', 'Unidades_Por_Bulk', 'Stock_Restante', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia', '%_Ganancia']]
        
        # Mostrar tabla
        st.write("### Resumen de Inventario")
        st.dataframe(tabla, use_container_width=True)
        
        # Métricas grandes
        c1, c2 = st.columns(2)
        c1.metric("Dinero Total en Ventas", f"C$ {ventas['Precio_Venta'].sum():.2f}")
        c2.metric("Ganancia Neta (Limpia)", f"C$ {ventas['Ganancia'].sum():.2f}")
    else:
        st.warning("No hay productos registrados.")
