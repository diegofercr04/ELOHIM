import streamlit as st
import pandas as pd
from datetime import datetime
from modulos.config.conexion import get_connection

def mostrar():
    st.title("🛒 Registro de Compras")
    conn = get_connection()
    if conn is None:
        st.error("Error de conexión."); return

    # ── Compras en espera ────────────────────────────────────────
    st.subheader("⏳ Compras pendientes de recibir")
    df_espera = pd.read_sql("""
        SELECT c.id, p.empresa AS proveedor, pr.nombre AS producto,
               c.cantidad, c.precio_unitario,
               (c.cantidad * c.precio_unitario) AS total, c.fecha
        FROM COMPRAS c
        JOIN PROVEEDORES p  ON c.id_proveedor = p.id
        JOIN PRODUCTOS   pr ON c.id_producto  = pr.id
        WHERE c.estado = 'espera'
        ORDER BY c.fecha DESC""", conn)

    if df_espera.empty:
        st.info("No hay compras pendientes.")
    else:
        for _, row in df_espera.iterrows():
            c_info, c_btn = st.columns([5, 2])
            c_info.markdown(
                f"**{row['producto']}** — {row['proveedor']}  \n"
                f"Cantidad: `{row['cantidad']}`  |  "
                f"Total: `${row['total']:.2f}`  |  "
                f"Fecha: `{row['fecha']}`"
            )
            if c_btn.button("✅ Marcar como recibida",
                            key=f"recibir_{row['id']}",
                            use_container_width=True):
                _confirmar_recepcion(row["id"], row["id"], row["cantidad"], conn)

    st.divider()

    # ── Historial de compras completadas ────────────────────────
    st.subheader("📋 Historial de compras completadas")
    df_hist = pd.read_sql("""
        SELECT c.id, p.empresa AS proveedor, pr.nombre AS producto,
               c.cantidad, c.precio_unitario,
               (c.cantidad * c.precio_unitario) AS total, c.fecha
        FROM COMPRAS c
        JOIN PROVEEDORES p  ON c.id_proveedor = p.id
        JOIN PRODUCTOS   pr ON c.id_producto  = pr.id
        WHERE c.estado = 'completada'
        ORDER BY c.fecha DESC""", conn)
    st.dataframe(df_hist, use_container_width=True)
    st.caption(f"{len(df_hist)} compra(s) completada(s)")
    st.divider()

    # ── Formulario nueva compra ──────────────────────────────────
    st.subheader("➕ Registrar nueva compra")
    df_prov = pd.read_sql("SELECT id, empresa FROM PROVEEDORES", conn)
    df_prod = pd.read_sql("SELECT id, nombre, stock FROM PRODUCTOS ORDER BY nombre", conn)

    if df_prov.empty:
        st.warning("⚠️ No hay proveedores registrados. Regístralos primero.")
        conn.close(); return

    c1, c2 = st.columns(2)
    with c1:
        prov_options = dict(zip(df_prov["empresa"], df_prov["id"]))
        prov_nombre  = st.selectbox("Proveedor", list(prov_options.keys()))
        id_proveedor = prov_options[prov_nombre]

        prod_options = {
            f"{r['nombre']} (stock actual: {r['stock']})": r["id"]
            for _, r in df_prod.iterrows()
        }
        prod_nombre = st.selectbox("Producto", list(prod_options.keys()))
        id_producto = prod_options[prod_nombre]

    with c2:
        cantidad        = st.number_input("Cantidad comprada", min_value=1, step=1)
        precio_unitario = st.number_input("Precio unitario ($)",
                                           min_value=0.0, format="%.2f")
        fecha_compra    = st.date_input("Fecha de compra", value=datetime.today())
        hora_compra     = st.time_input("Hora de compra",  value=datetime.now().time())

    st.info(f"💵 Total de esta compra: **${cantidad * precio_unitario:.2f}**")

    if st.button("💾 Registrar compra (en espera)",
                 use_container_width=True, type="primary"):
        fecha_hora = datetime.combine(fecha_compra, hora_compra)
        cursor     = conn.cursor()
        cursor.execute("""
            INSERT INTO COMPRAS
            (id_proveedor, id_producto, cantidad, precio_unitario, fecha, estado)
            VALUES (%s, %s, %s, %s, %s, 'espera')""",
            (id_proveedor, id_producto, cantidad, precio_unitario, fecha_hora))
        conn.commit()
        conn.close()
        st.success("✅ Compra registrada en espera. Se sumará al inventario cuando se confirme la recepción.")
        st.rerun()

def _confirmar_recepcion(id_compra, id_compra_dup, cantidad, conn):
    # Obtener id_producto real de la compra
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id_producto, cantidad FROM COMPRAS WHERE id = %s", (id_compra,))
    compra = cur.fetchone()
    if not compra: return

    # 1. Actualizar estado de la compra
    cur.execute(
        "UPDATE COMPRAS SET estado = 'completada' WHERE id = %s", (id_compra,))

    # 2. Sumar cantidad al inventario
    cur.execute(
        "UPDATE PRODUCTOS SET stock = stock + %s WHERE id = %s",
        (compra["cantidad"], compra["id_producto"]))

    conn.commit()
    conn.close()
    st.success("✅ Compra confirmada. El inventario fue actualizado.")
    st.rerun()
