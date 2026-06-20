import streamlit as st
import pandas as pd
from datetime import datetime
from modulos.config.conexion import get_connection

def mostrar():
    st.title("🛒 Registro de Compras")
    conn = get_connection()
    if conn is None:
        st.error("Error de conexión."); return

    # ── Historial de compras ────────────────────────────────────
    st.subheader("📋 Historial de compras")
    df_hist = pd.read_sql("""
        SELECT c.id, p.empresa AS proveedor, pr.nombre AS producto,
               c.cantidad, c.precio_unitario,
               (c.cantidad * c.precio_unitario) AS total,
               c.fecha
        FROM COMPRAS c
        JOIN PROVEEDORES p  ON c.id_proveedor = p.id
        JOIN PRODUCTOS   pr ON c.id_producto  = pr.id
        ORDER BY c.fecha DESC
    """, conn)
    st.dataframe(df_hist, use_container_width=True)
    st.caption(f"{len(df_hist)} compra(s) registrada(s)")
    st.divider()

    # ── Formulario de nueva compra ──────────────────────────────
    st.subheader("➕ Registrar nueva compra")

    df_prov = pd.read_sql("SELECT id, empresa FROM PROVEEDORES", conn)
    df_prod = pd.read_sql("SELECT id, nombre, stock FROM PRODUCTOS", conn)

    if df_prov.empty:
        st.warning("⚠️ No hay proveedores registrados. Regístralos primero.")
        conn.close(); return

    c1, c2 = st.columns(2)
    with c1:
        # Selector de proveedor
        prov_options = dict(zip(df_prov["empresa"], df_prov["id"]))
        prov_nombre  = st.selectbox("Proveedor", list(prov_options.keys()))
        id_proveedor = prov_options[prov_nombre]

        # Selector de producto
        prod_options = {
            f"{r['nombre']} (stock: {r['stock']})": r["id"]
            for _, r in df_prod.iterrows()
        }
        prod_nombre  = st.selectbox("Producto", list(prod_options.keys()))
        id_producto  = prod_options[prod_nombre]

    with c2:
        cantidad        = st.number_input("Cantidad comprada", min_value=1, step=1)
        precio_unitario = st.number_input("Precio unitario de compra ($)",
                                           min_value=0.0, format="%.2f")
        fecha_compra    = st.date_input("Fecha de compra", value=datetime.today())
        hora_compra     = st.time_input("Hora de compra", value=datetime.now().time())

    total_compra = cantidad * precio_unitario
    st.info(f"💵 Total de esta compra: **${total_compra:.2f}**")

    if st.button("💾 Confirmar compra", use_container_width=True, type="primary"):
        fecha_hora = datetime.combine(fecha_compra, hora_compra)
        cursor     = conn.cursor()

        # 1. Insertar registro de compra
        cursor.execute("""
            INSERT INTO COMPRAS
            (id_proveedor, id_producto, cantidad, precio_unitario, fecha)
            VALUES (%s, %s, %s, %s, %s)""",
            (id_proveedor, id_producto, cantidad, precio_unitario, fecha_hora))

        # 2. Sumar automáticamente al stock del producto
        cursor.execute("""
            UPDATE PRODUCTOS
            SET stock = stock + %s
            WHERE id = %s""", (cantidad, id_producto))

        conn.commit()
        conn.close()
        st.success(f"✅ Compra registrada. Se sumaron {cantidad} unidades al inventario.")
        st.rerun()
