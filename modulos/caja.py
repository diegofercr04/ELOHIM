import streamlit as st
import pandas as pd
from modulos.config.conexion import get_connection


def mostrar():
    st.title("💰 Arqueo de Caja")
    conn = get_connection()
    if conn is None:
        st.error("Error de conexión."); return

    fecha = st.date_input("Seleccionar fecha de arqueo")
    st.divider()

    # ── Ventas del día ───────────────────────────────────────────
    df_ventas_met = pd.read_sql("""
        SELECT metodo_pago,
               SUM(total)  AS total_ingresado,
               COUNT(*)    AS num_ventas
        FROM VENTAS
        WHERE DATE(fecha) = %s
        GROUP BY metodo_pago""", conn, params=(str(fecha),))

    efectivo      = df_ventas_met[df_ventas_met["metodo_pago"]=="efectivo"]["total_ingresado"].sum()
    transferencia = df_ventas_met[df_ventas_met["metodo_pago"]=="transferencia"]["total_ingresado"].sum()
    total_ventas  = efectivo + transferencia

    # ── Compras completadas del día ──────────────────────────────
    df_compras_dia = pd.read_sql("""
        SELECT SUM(cantidad * precio_unitario) AS total_compras,
               COUNT(*) AS num_compras
        FROM COMPRAS
        WHERE DATE(fecha) = %s AND estado = 'completada'""",
        conn, params=(str(fecha),))

    total_compras = df_compras_dia["total_compras"].fillna(0).iloc[0]
    num_compras   = df_compras_dia["num_compras"].iloc[0]

    # ── Balance neto ─────────────────────────────────────────────
    beneficio_neto = total_ventas - total_compras

    # ── Métricas principales ─────────────────────────────────────
    st.subheader("📊 Resumen del día")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 Ventas efectivo",      f"${efectivo:.2f}")
    c2.metric("🏦 Ventas transferencia", f"${transferencia:.2f}")
    c3.metric("📦 Total ventas",         f"${total_ventas:.2f}")
    c4.metric("🛒 Total compras",        f"${total_compras:.2f}")

    st.divider()

    # ── Balance neto destacado ───────────────────────────────────
    if beneficio_neto >= 0:
        st.success(f"✅ Beneficio neto del día: **${beneficio_neto:.2f}**")
    else:
        st.error(f"⚠️ Balance negativo del día: **${beneficio_neto:.2f}**")

    st.divider()

    # ── Detalle ventas ───────────────────────────────────────────
    st.subheader("🧾 Ventas del día")
    conn2     = get_connection()
    df_ventas = pd.read_sql("""
        SELECT v.id, v.fecha, v.total, v.metodo_pago,
               GROUP_CONCAT(p.nombre SEPARATOR ', ') AS productos
        FROM VENTAS v
        JOIN DETALLE_VENTA dv ON dv.id_venta   = v.id
        JOIN PRODUCTOS     p  ON dv.id_producto = p.id
        WHERE DATE(v.fecha) = %s
        GROUP BY v.id ORDER BY v.fecha DESC""",
        conn2, params=(str(fecha),))
    st.dataframe(df_ventas, use_container_width=True)

    # ── Detalle compras ──────────────────────────────────────────
    st.subheader("🛒 Compras completadas del día")
    conn3       = get_connection()
    df_compras  = pd.read_sql("""
        SELECT c.id, p.empresa AS proveedor, pr.nombre AS producto,
               c.cantidad, c.precio_unitario,
               (c.cantidad * c.precio_unitario) AS total, c.fecha
        FROM COMPRAS c
        JOIN PROVEEDORES p  ON c.id_proveedor = p.id
        JOIN PRODUCTOS   pr ON c.id_producto  = pr.id
        WHERE DATE(c.fecha) = %s AND c.estado = 'completada'
        ORDER BY c.fecha DESC""",
        conn3, params=(str(fecha),))
    st.dataframe(df_compras, use_container_width=True)
    st.caption(f"{num_compras} compra(s) completada(s) en este día")

    conn.close()
    conn2.close()
    conn3.close()
