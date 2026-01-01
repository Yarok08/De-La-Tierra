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
opcion = st.sidebar.selectbox("Menú", ["Registrar Ventas", "Inventario Real", "Dashboard", "Editar Productos", "Gestión (Reset)"])

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
                    cost_u = p['Costo_Por_Bulk'] / p['Unidades_Por_Bulk']
                    ganancia_v = m['precio'] - (m['unidades'] * cost_u)
                    
                    nv = pd.DataFrame([{'Fecha': datetime.now(), 'Nombre': p['Nombre'], 'Modo': m['nombre'], 'Unidades_Vendidas': m['unidades'], 'Precio_Venta': m['precio'], 'Ganancia': round(ganancia_v, 2), 'Empleado': st.session_state['empleado']}])
                    ventas = pd.concat([ventas, nv], ignore_index=True)
                    guardar_datos(productos, ventas)
                    st.success("✅ Venta Guardada")
                    st.rerun()

# --- INVENTARIO REAL (AQUÍ ESTÁ LA CORRECCIÓN) ---
elif opcion == "Inventario Real":
    st.header("📋 Control de Inventario y Ganancias")
    
    if not productos.empty:
        # Calculamos todo dinámicamente
        resumen_ventas = ventas.groupby('Nombre').agg({
            'Unidades_Vendidas': 'sum',
            'Precio_Venta': 'sum',
            'Ganancia': 'sum'
        }).reset_index()
        
        # Unimos con la tabla de productos
        df_inv = pd.merge(productos, resumen_ventas, on='Nombre', how='left').fillna(0)
        
        # Calculamos Stock Restante
        df_inv['Stock_Restante_Unidades'] = df_inv['Unidades_Por_Bulk'] - df_inv['Unidades_Vendidas']
        
        # Calculamos % de Ganancia sobre la venta
        df_inv['%_Margen'] = (df_inv['Ganancia'] / df_inv['Precio_Venta'] * 100).fillna(0).round(2)
        
        # Seleccionamos y renombramos columnas para que sea claro para ti
        final_table = df_inv[[
            'Nombre', 
            'Unidades_Por_Bulk', 
            'Stock_Restante_Unidades', 
            'Unidades_Vendidas', 
            'Precio_Venta', 
            'Ganancia', 
            '%_Margen'
        ]]
        
        st.dataframe(final_table.style.format({
            'Precio_Venta': 'C${:.2f}',
            'Ganancia': 'C${:.2f}',
            '%_Margen': '{:.2f}%'
        }), use_container_width=True)
        
        st.info("💡 'Precio_Venta' es el dinero total que ha entrado. 'Ganancia' es lo que te queda limpio después de quitar el costo.")
    else:
        st.warning("No hay productos configurados.")

# --- DASHBOARD ---
elif opcion == "Dashboard":
    st.header("📈 Rendimiento")
    if not ventas.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Ventas Totales", f"C$ {ventas['Precio_Venta'].sum():.2f}")
        c2.metric("Ganancia Limpia", f"C$ {ventas['Ganancia'].sum():.2f}")
        # Margen promedio
        margen = (ventas['Ganancia'].sum() / ventas['Precio_Venta'].sum() * 100) if ventas['Precio_Venta'].sum() > 0 else 0
        c3.metric("Margen Promedio", f"{margen:.2f}%")
        
        st.bar_chart(ventas.groupby('Nombre')['Ganancia'].sum())
    else:
        st.info("Sin ventas registradas.")

# --- RESTO DE OPCIONES (EDITAR, ETC) ---
elif opcion == "Editar Productos":
    st.header("📝 Editar")
    p_edit = st.selectbox("Producto:", productos['Nombre'])
    idx = productos[productos['Nombre'] == p_edit].index[0]
    with st.form("edit"):
        nuevo_n = st.text_input("Nombre", value=productos.at[idx, 'Nombre'])
        c_b = st.number_input("Costo Bulto", value=float(productos.at[idx, 'Costo_Por_Bulk']))
        u_b = st.number_input("Unidades en Bulto", value=int(productos.at[idx, 'Unidades_Por_Bulk']))
        if st.form_submit_button("Guardar Cambios"):
            productos.at[idx, 'Nombre'] = nuevo_n
            productos.at[idx, 'Costo_Por_Bulk'] = c_b
            productos.at[idx, 'Unidades_Por_Bulk'] = u_b
            guardar_datos(productos, ventas)
            st.success("Actualizado")
            st.rerun()
