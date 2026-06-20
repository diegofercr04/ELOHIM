import streamlit as st
import pandas as pd
from modulos.config.conexion import get_connection

def mostrar():
    st.title("💰 Arqueo de Caja")
    conn = get_connection()
    if conn is None:
        st.error("Error de conexión."); return

    fecha = st.date_input("Seleccionar fecha de arqueo")

    q = """
        SELECT metodo_pago,
               SUM(total) AS total_ingresado,
               COUNT(*) AS num_ventas
        FROM VENTAS
        WHERE DATE(fecha) = %s
        GROUP BY metodo_pago"""
    df = pd.read_sql(q, conn, params=(str(fecha),))
    conn.close()

    if df.empty:
        st.info(f"No hay ventas registradas para {fecha}.")
        return

    efectivo     = df[df["metodo_pago"]=="efectivo"]["total_ingresado"].sum()
    transferencia= df[df["metodo_pago"]=="transferencia"]["total_ingresado"].sum()
    total        = efectivo + transferencia

    c1, c2, c3 = st.columns(3)
    c1.metric("💵 Efectivo",      f"${efectivo:.2f}")
    c2.metric("🏦 Transferencias", f"${transferencia:.2f}")
    c3.metric("📦 Total del día",  f"${total:.2f}")

    st.divider()
    st.subheader("Detalle por método de pago")
    st.dataframe(df, use_container_width=True)

    st.divider()
    st.subheader("📋 Ventas del día")
    conn2 = get_connection()
    df_ventas = pd.read_sql("""
        SELECT v.id, v.total, v.metodo_pago, v.fecha
        FROM VENTAS v WHERE DATE(fecha) = %s
        ORDER BY v.fecha DESC""",
        conn2, params=(str(fecha),))
    conn2.close()
    st.dataframe(df_ventas, use_container_width=True)
