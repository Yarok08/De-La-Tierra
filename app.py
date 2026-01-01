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
    if not v.empty:
        v['Fecha'] = pd.to_datetime(v['Fecha'], format='mixed')
    return p, v

def guardar_datos(p, v):
    p.to_csv('productos.csv', index=False)
    v.to_csv('ventas.csv', index=False)

productos, ventas = cargar_datos()

# --- MENÚ ---
st.sidebar.title(f"👤 {st.session_state['empleado']}")
opcion = st.sidebar.selectbox("Menú Principal", [
    "🛒 Registrar Venta", "📋 Inventario Real", "📊 Dashboard", 
    "📅 Registro Mensual", "✨ Configurar Productos", "📥 Añadir Stock",
    "✏️ Editar Producto", "⚙️ Gestión (Reset)"
])

# 1. REGISTRAR VENTA
if opcion == "🛒 Registrar Venta":
    st.header("🛒 Terminal de Ventas")
    if productos.empty:
        st.warning("Primero configura un producto en la pestaña ✨")
    else:
        busqueda = st.text_input("🔍 Buscar...")
        df_m = productos[productos['Nombre'].str.contains(busqueda, case=False)] if busqueda else productos
        for idx, p_row in df_m.iterrows():
            with st.expander(f"📦 {p_row['Nombre']}"):
                modos = eval(p_row['Modos'])
                cols = st.columns(len(modos))
                for m_idx, m in enumerate(modos):
                    if cols[m_idx].button(f"{m['nombre']}\nC${m['precio']}", key=f"v_{idx}_{m_idx}"):
                        # Cálculo de costo unitario actual
                        cost_u = p_row['Costo_Por_Bulk'] / p_row['Unidades_Por_Bulk']
                        ganancia_v = m['precio'] - (m['unidades'] * cost_u)
                        nv = pd.DataFrame([{'Fecha': datetime.now(), 'Nombre': p_row['Nombre'], 'Modo': m['nombre'], 'Unidades_Vendidas': m['unidades'], 'Precio_Venta': m['precio'], 'Ganancia': round(ganancia_v, 2), 'Empleado': st.session_state['empleado']}])
                        ventas = pd.concat([ventas, nv], ignore_index=True)
                        guardar_datos(productos, ventas)
                        st.success(f"¡Venta de {m['nombre']} realizada!")
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

# 3. DASHBOARD Y 4. MENSUAL
elif opcion == "📊 Dashboard":
    st.header("📊 Resumen de Negocio")
    if not ventas.empty:
        col1, col2 = st.columns(2)
        col1.metric("Ingreso Total", f"C$ {ventas['Precio_Venta'].sum():.2f}")
        col2.metric("Ganancia Limpia", f"C$ {ventas['Ganancia'].sum():.2f}")
        st.bar_chart(ventas.groupby('Nombre')['Ganancia'].sum())

elif opcion == "📅 Registro Mensual":
    st.header("📅 Historial por Mes")
    if not ventas.empty:
        ventas['Mes'] = ventas['Fecha'].dt.strftime('%Y-%m')
        mes = st.selectbox("Mes:", ventas['Mes'].unique())
        st.write(ventas[ventas['Mes'] == mes])

# 5. CONFIGURAR PRODUCTOS
elif opcion == "✨ Configurar Productos":
    st.header("✨ Nuevo Producto")
    with st.form("f1"):
        n = st.text_input("Nombre del Producto")
        cb = st.number_input("Costo del Bulto Completo", 0.0)
        ub = st.number_input("Unidades totales en el Bulto", 1)
        st.subheader("Opciones / Modos de Venta (Hasta 5)")
        modos_lista = []
        for i in range(5):
            st.write(f"Modo {i+1}")
            c1, c2, c3 = st.columns(3)
            m_nom = c1.text_input("Etiqueta", key=f"n_{i}")
            m_uni = c2.number_input("Unidades", min_value=1, key=f"u_{i}")
            m_pre = c3.number_input("Precio C$", 0.0, key=f"p_{i}")
            if m_nom != "": modos_lista.append({'nombre': m_nom, 'unidades': m_uni, 'precio': m_pre})
        if st.form_submit_button("Guardar Producto"):
            if n != "" and len(modos_lista) > 0:
                new = pd.DataFrame([{'Nombre': n, 'Unidades_Por_Bulk': ub, 'Costo_Por_Bulk': cb, 'Modos': str(modos_lista)}])
                productos = pd.concat([productos, new], ignore_index=True)
                guardar_datos(productos, ventas)
                st.success("Producto creado.")
                st.rerun()

# 6. AÑADIR STOCK (CON COSTO PROMEDIO)
elif opcion == "📥 Añadir Stock":
    st.header("📥 Registro de Nueva Compra")
    if not productos.empty:
        p_sel = st.selectbox("Selecciona Producto:", productos['Nombre'])
        idx = productos[productos['Nombre'] == p_sel].index[0]
        
        # Datos actuales para el cálculo
        v_tot = ventas[ventas['Nombre'] == p_sel]['Unidades_Vendidas'].sum()
        unidades_actuales = productos.at[idx, 'Unidades_Por_Bulk'] - v_tot
        costo_bulto_actual = productos.at[idx, 'Costo_Por_Bulk']
        unidades_en_bulto_actual = productos.at[idx, 'Unidades_Por_Bulk']
        
        costo_unitario_actual = costo_bulto_actual / unidades_en_bulto_actual
        valor_inventario_actual = unidades_actuales * costo_unitario_actual
        
        st.info(f"Tienes actualmente **{unidades_actuales}** unidades en stock.")
        
        with st.form("stock_form"):
            unid_nuevas = st.number_input("¿Cuántas unidades nuevas compraste?", min_value=1)
            costo_nuevo_total = st.number_input("¿Cuánto pagaste por estas unidades nuevas en total? (C$)", min_value=0.0)
            
            if st.form_submit_button("Registrar Compra y Promediar"):
                # Cálculo de Promedio Ponderado
                # Valor Total = Valor Viejo + Valor Nuevo
                # Unidades Totales = Unidades Viejas + Unidades Nuevas
                valor_total = valor_inventario_actual + costo_nuevo_total
                unidades_totales_finales = unidades_actuales + unid_nuevas
                
                # Para mantener la estructura del bulto, actualizamos el costo del bulto 
                # proporcionalmente a las unidades totales registradas.
                nuevo_costo_unidad = valor_total / unidades_totales_finales
                
                # Actualizamos el CSV: sumamos las unidades y ajustamos el costo de bulto 
                # para que el costo unitario (Costo_Por_Bulk / Unidades_Por_Bulk) sea el promedio.
                productos.at[idx, 'Unidades_Por_Bulk'] += unid_nuevas
                productos.at[idx, 'Costo_Por_Bulk'] = round(nuevo_costo_unidad * productos.at[idx, 'Unidades_Por_Bulk'], 2)
                
                guardar_datos(productos, ventas)
                st.success(f"¡Compra registrada! El nuevo costo promedio por unidad es C$ {nuevo_costo_unidad:.2f}")
                st.rerun()
    else: st.warning("No hay productos registrados.")

# 7. EDITAR PRODUCTO 
elif opcion == "✏️ Editar Producto":
    st.header("✏️ Modificar Producto Existente")
    if not productos.empty:
        p_edit = st.selectbox("Selecciona producto a editar:", productos['Nombre'])
        idx = productos[productos['Nombre'] == p_edit].index[0]
        p_data = productos.iloc[idx]
        modos_actuales = eval(p_data['Modos'])
        
        with st.form("edit_form"):
            new_n = st.text_input("Nombre del Producto:", value=p_data['Nombre'])
            new_cb = st.number_input("Costo Bulto Actual (Promediado):", value=float(p_data['Costo_Por_Bulk']))
            new_ub = st.number_input("Total de unidades históricas:", value=int(p_data['Unidades_Por_Bulk']))
            
            st.subheader("Editar Modos de Venta")
            nuevos_modos = []
            for i in range(5):
                val_nom = modos_actuales[i]['nombre'] if i < len(modos_actuales) else ""
                val_uni = modos_actuales[i]['unidades'] if i < len(modos_actuales) else 1
                val_pre = modos_actuales[i]['precio'] if i < len(modos_actuales) else 0.0
                st.write(f"Opción {i+1}")
                c1, c2, c3 = st.columns(3)
                m_nom = c1.text_input("Etiqueta", value=val_nom, key=f"en_{i}")
                m_uni = c2.number_input("Unidades", min_value=1, value=int(val_uni), key=f"eu_{i}")
                m_pre = c3.number_input("Precio C$", value=float(val_pre), key=f"ep_{i}")
                if m_nom != "": nuevos_modos.append({'nombre': m_nom, 'unidades': m_uni, 'precio': m_pre})
            
            if st.form_submit_button("Actualizar Todo"):
                productos.at[idx, 'Nombre'] = new_n
                productos.at[idx, 'Costo_Por_Bulk'] = new_cb
                productos.at[idx, 'Unidades_Por_Bulk'] = new_ub
                productos.at[idx, 'Modos'] = str(nuevos_modos)
                guardar_datos(productos, ventas)
                st.success("✅ Producto actualizado.")
                st.rerun()

# 8. GESTIÓN (RESET)
elif opcion == "⚙️ Gestión (Reset)":
    st.header("⚙️ Limpieza")
    if st.button("🚨 BORRAR SOLO VENTAS"):
        guardar_datos(productos, pd.DataFrame(columns=['Fecha', 'Nombre', 'Modo', 'Unidades_Vendidas', 'Precio_Venta', 'Ganancia', 'Empleado']))
        st.rerun()
    if st.button("🧨 RESETEAR TODO"):
        if os.path.exists('productos.csv'): os.remove('productos.csv')
        if os.path.exists('ventas.csv'): os.remove('ventas.csv')
        st.rerun()
