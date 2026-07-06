import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from modulos.config.conexion import get_connection

SV_TZ = pytz.timezone("America/El_Salvador")


def _agregar_a_carrito_compra(prod_id, prod_nombre, cantidad, precio_unit):
    if "carrito_compra" not in st.session_state:
        st.session_state["carrito_compra"] = []
    for item in st.session_state["carrito_compra"]:
        if item["id_producto"] == prod_id:
            item["cantidad"] += cantidad
            return
    st.session_state["carrito_compra"].append({
        "id_producto":   prod_id,
        "nombre":        prod_nombre,
        "cantidad":      cantidad,
        "precio_unit":   precio_unit,
    })


def mostrar():
    st.title("🛒 Registro de Compras")

    if "carrito_compra" not in st.session_state:
        st.session_state["carrito_compra"] = []

    conn = get_connection()
    if conn is None:
        st.error("Error de conexión."); return

    df_prov = pd.read_sql("SELECT id, empresa FROM PROVEEDORES", conn)
    df_prod = pd.read_sql("SELECT id, nombre, stock FROM PRODUCTOS ORDER BY nombre", conn)

    if df_prov.empty:
        st.warning("⚠️ No hay proveedores registrados.")
        conn.close(); return

    # ── Formulario agregar al carrito ────────────────────────────
    st.subheader("➕ Agregar producto a la orden")
    c1, c2 = st.columns(2)
    with c1:
        prod_options = {
            f"{r['nombre']} (stock: {r['stock']})": (r["id"], r["nombre"])
            for _, r in df_prod.iterrows()
        }
        prod_sel    = st.selectbox("Producto", list(prod_options.keys()), key="cp_prod")
        prod_id, prod_nombre = prod_options[prod_sel]
    with c2:
        cantidad_item    = st.number_input("Cantidad", min_value=1, step=1, key="cp_cant")
        precio_unit_item = st.number_input("Precio unitario ($)", min_value=0.0,
                                            format="%.2f", key="cp_precio")

    if st.button("🛒 Agregar a la orden", use_container_width=True, key="cp_add"):
        _agregar_a_carrito_compra(prod_id, prod_nombre, cantidad_item, precio_unit_item)
        st.rerun()

    # ── Carrito de compra ────────────────────────────────────────
    st.divider()
    st.subheader("📋 Orden de compra actual")

    if not st.session_state["carrito_compra"]:
        st.info("La orden está vacía. Agrega productos arriba.")
    else:
        for i, item in enumerate(st.session_state["carrito_compra"]):
            subtotal = item["cantidad"] * item["precio_unit"]
            c_nom, c_qty, c_sub, c_del = st.columns([4, 2, 2, 1])
            c_nom.write(item["nombre"])
            c_qty.write(f"{item['cantidad']} × ${item['precio_unit']:.2f}")
            c_sub.write(f"**${subtotal:.2f}**")
            if c_del.button("✕", key=f"cp_del_{i}"):
                st.session_state["carrito_compra"].pop(i)
                st.rerun()

        total_orden = sum(
            x["cantidad"] * x["precio_unit"]
            for x in st.session_state["carrito_compra"]
        )
        st.metric("💵 Total de la orden", f"${total_orden:.2f}")

        if st.button("🗑️ Vaciar orden", key="cp_vaciar"):
            st.session_state["carrito_compra"] = []
            st.rerun()

        # ── Confirmar orden completa ─────────────────────────────────
        st.divider()
        st.subheader("✅ Confirmar orden de compra")
        prov_options  = dict(zip(df_prov["empresa"], df_prov["id"]))
        prov_nombre   = st.selectbox("Proveedor", list(prov_options.keys()), key="cp_prov")
        id_proveedor  = prov_options[prov_nombre]
        ahora_sv      = datetime.now(SV_TZ)
        c1, c2        = st.columns(2)
        fecha_compra  = c1.date_input("Fecha", value=ahora_sv.date(), key="cp_fecha")
        hora_compra   = c2.time_input("Hora",  value=ahora_sv.time().replace(tzinfo=None),
                                       key="cp_hora")

        if st.button("💾 Registrar orden completa (en espera)",
                     use_container_width=True, type="primary", key="cp_confirmar"):
            fecha_hora = SV_TZ.localize(datetime.combine(fecha_compra, hora_compra))
            cursor     = conn.cursor()
            for item in st.session_state["carrito_compra"]:
                cursor.execute("""
                    INSERT INTO COMPRAS
                    (id_proveedor, id_producto, cantidad, precio_unitario, fecha, estado)
                    VALUES (%s,%s,%s,%s,%s,'espera')""",
                    (id_proveedor, item["id_producto"],
                     item["cantidad"], item["precio_unit"], fecha_hora))
            conn.commit()
            conn.close()
            st.session_state["carrito_compra"] = []
            st.success("✅ Orden registrada en espera. Confirma cuando llegue la mercadería.")
            st.rerun()

    # ── Compras en espera ────────────────────────────────────────
    st.divider()
    st.subheader("⏳ Compras pendientes de recibir")
    conn2 = get_connection()
    df_espera = pd.read_sql("""
        SELECT c.id, p.empresa AS proveedor, pr.nombre AS producto,
               c.cantidad, c.precio_unitario,
               (c.cantidad * c.precio_unitario) AS total, c.fecha
        FROM COMPRAS c
        JOIN PROVEEDORES p  ON c.id_proveedor = p.id
        JOIN PRODUCTOS   pr ON c.id_producto  = pr.id
        WHERE c.estado = 'espera'
        ORDER BY c.fecha DESC""", conn2)

    if df_espera.empty:
        st.info("No hay compras pendientes.")
    else:
        for _, row in df_espera.iterrows():
            c_info, c_btn = st.columns([5, 2])
            c_info.markdown(
                f"**{row['producto']}** — {row['proveedor']}  \n"
                f"Cantidad: `{row['cantidad']}`  |  Total: `${row['total']:.2f}`  |  Fecha: `{row['fecha']}`"
            )
            if c_btn.button("✅ Marcar recibida", key=f"recibir_{row['id']}",
                            use_container_width=True):
                _confirmar_recepcion(row["id"], conn2)

    # ── Historial completadas ────────────────────────────────────
    st.divider()
    st.subheader("📋 Historial de compras completadas")
    conn3 = get_connection()
    df_hist = pd.read_sql("""
        SELECT c.id, p.empresa AS proveedor, pr.nombre AS producto,
               c.cantidad, c.precio_unitario,
               (c.cantidad * c.precio_unitario) AS total, c.fecha
        FROM COMPRAS c
        JOIN PROVEEDORES p  ON c.id_proveedor = p.id
        JOIN PRODUCTOS   pr ON c.id_producto  = pr.id
        WHERE c.estado = 'completada'
        ORDER BY c.fecha DESC""", conn3)
    st.dataframe(df_hist, use_container_width=True)
    conn3.close()


def _confirmar_recepcion(id_compra, conn):
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id_producto, cantidad FROM COMPRAS WHERE id = %s", (id_compra,))
    compra = cur.fetchone()
    if not compra: return
    cur.execute("UPDATE COMPRAS SET estado='completada' WHERE id=%s", (id_compra,))
    cur.execute("UPDATE PRODUCTOS SET stock=stock+%s WHERE id=%s",
               (compra["cantidad"], compra["id_producto"]))
    conn.commit()
    conn.close()
    st.success("✅ Recibida. Inventario actualizado.")
    st.rerun()
