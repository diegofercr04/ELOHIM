import streamlit as st
import pandas as pd
from modulos.config.conexion import get_connection

def mostrar():
    st.title("📊 Reportes e Inteligencia de Negocio")
    conn = get_connection()
    if conn is None:
        st.error("Error de conexión."); return

    tab1, tab2, tab3 = st.tabs([
        "⭐ Producto Estrella",
        "📅 Estadísticas Mensuales",
        "📉 Baja Rotación"
    ])

    with tab1:
        st.subheader("Top 10 productos más vendidos")
        q = """
            SELECT p.nombre, SUM(dv.cantidad) AS unidades_vendidas,
                   SUM(dv.cantidad * dv.precio_unitario) AS ingresos
            FROM DETALLE_VENTA dv
            JOIN PRODUCTOS p ON dv.id_producto = p.id
            GROUP BY p.id, p.nombre
            ORDER BY ingresos DESC LIMIT 10"""
        df_top = pd.read_sql(q, conn)
        if not df_top.empty:
            estrella = df_top.iloc[0]
            st.success(f"🥇 Producto estrella: **{estrella['nombre']}**"
                       f" — ${estrella['ingresos']:.2f} en ingresos")
            st.bar_chart(df_top.set_index("nombre")["ingresos"])
            st.dataframe(df_top, use_container_width=True)
        else:
            st.info("Aún no hay ventas registradas.")

    with tab2:
        st.subheader("Ventas mensuales históricas")
        q2 = """
            SELECT DATE_FORMAT(v.fecha, '%Y-%m') AS mes,
                   SUM(dv.cantidad * dv.precio_unitario) AS total
            FROM VENTAS v
            JOIN DETALLE_VENTA dv ON dv.id_venta = v.id
            GROUP BY mes ORDER BY mes"""
        df_mes = pd.read_sql(q2, conn)
        if not df_mes.empty:
            st.line_chart(df_mes.set_index("mes")["total"])
            st.dataframe(df_mes, use_container_width=True)
        else:
            st.info("Aún no hay datos mensuales.")

    with tab3:
        st.subheader("Productos con baja o nula rotación")
        q3 = """
            SELECT p.nombre, p.categoria, p.stock,
                   COALESCE(SUM(dv.cantidad), 0) AS unidades_vendidas
            FROM PRODUCTOS p
            LEFT JOIN DETALLE_VENTA dv ON dv.id_producto = p.id
            GROUP BY p.id
            HAVING unidades_vendidas < 5
            ORDER BY unidades_vendidas ASC"""
        df_baja = pd.read_sql(q3, conn)
        st.dataframe(df_baja, use_container_width=True)
        st.caption("Productos con menos de 5 unidades vendidas históricamente.")
    conn.close()
