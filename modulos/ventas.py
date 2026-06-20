import streamlit as st
import pandas as pd
from datetime import datetime
from modulos.config.conexion import get_connection

def mostrar():
    st.title("🧾 Registro de Ventas")

    # Inicializar carrito en session_state
    if "carrito" not in st.session_state:
        st.session_state["carrito"] = []

    conn = get_connection()
    if conn is None:
        st.error("Error de conexión."); return

    # Solo productos con stock disponible
    df_prod = pd.read_sql(
        "SELECT id, nombre, precio_venta, stock FROM PRODUCTOS WHERE stock > 0 ORDER BY nombre",
        conn)

    if df_prod.empty:
        st.warning("⚠️ No hay productos con stock disponible.")
        conn.close(); return

    # ── Sección izquierda: agregar producto al carrito ──────────
    col_form, col_carrito = st.columns([1, 1])

    with col_form:
        st.subheader("➕ Agregar producto")

        prod_map = {
            f"{r['nombre']}  —  ${r['precio_venta']:.2f}  (stock: {r['stock']})": r
            for _, r in df_prod.iterrows()
        }
        prod_sel  = st.selectbox("Producto", list(prod_map.keys()))
        prod_info = prod_map[prod_sel]

        # Limitar cantidad al stock disponible
        cant = st.number_input(
            "Cantidad", min_value=1,
            max_value=int(prod_info["stock"]), step=1)

        if st.button("🛒 Agregar al carrito", use_container_width=True):
            # Verificar si el producto ya está en el carrito
            existe = False
            for item in st.session_state["carrito"]:
                if item["id"] == prod_info["id"]:
                    item["cantidad"] += cant
                    existe = True; break
            if not existe:
                st.session_state["carrito"].append({
                    "id":             int(prod_info["id"]),
                    "nombre":         prod_info["nombre"],
                    "precio_unitario": float(prod_info["precio_venta"]),
                    "cantidad":       cant,
                    "stock_disponible": int(prod_info["stock"])
                })
            st.rerun()

    # ── Sección derecha: carrito actual ─────────────────────────
    with col_carrito:
        st.subheader("🛒 Carrito actual")
        if not st.session_state["carrito"]:
            st.info("El carrito está vacío.")
        else:
            for i, item in enumerate(st.session_state["carrito"]):
                subtotal = item["cantidad"] * item["precio_unitario"]
                c_name, c_btn = st.columns([4, 1])
                c_name.markdown(
                    f"**{item['nombre']}**  \n"
                    f"{item['cantidad']} × ${item['precio_unitario']:.2f} = **${subtotal:.2f}**")
                if c_btn.button("✕", key=f"del_{i}"):
                    st.session_state["carrito"].pop(i)
                    st.rerun()

            total_venta = sum(
                x["cantidad"] * x["precio_unitario"]
                for x in st.session_state["carrito"])
            st.metric("Total de la venta", f"${total_venta:.2f}")

            if st.button("🗑️ Vaciar carrito", use_container_width=True):
                st.session_state["carrito"] = []
                st.rerun()

    # ── Confirmación de venta ───────────────────────────────────
    if st.session_state["carrito"]:
        st.divider()
        st.subheader("✅ Confirmar venta")
        c1, c2, c3 = st.columns(3)
        with c1:
            metodo_pago  = st.radio("Método de pago",
                                    ["efectivo", "transferencia"], horizontal=True)
        with c2:
            fecha_venta  = st.date_input("Fecha", value=datetime.today())
        with c3:
            hora_venta   = st.time_input("Hora", value=datetime.now().time())

        total_final = sum(
            x["cantidad"] * x["precio_unitario"]
            for x in st.session_state["carrito"])

        st.success(f"💵 Total a cobrar: **${total_final:.2f}** — Pago en **{metodo_pago}**")

        if st.button("✅ Confirmar y registrar venta",
                     use_container_width=True, type="primary"):
            fecha_hora = datetime.combine(fecha_venta, hora_venta)
            cursor     = conn.cursor()

            # 1. Insertar cabecera de venta
            cursor.execute("""
                INSERT INTO VENTAS (fecha, total, metodo_pago, usuario_id)
                VALUES (%s, %s, %s, %s)""",
                (fecha_hora, total_final, metodo_pago,
                 st.session_state.get("usuario_id", None)))
            id_venta = cursor.lastrowid

            # 2. Insertar detalle + descontar stock por cada producto
            for item in st.session_state["carrito"]:
                cursor.execute("""
                    INSERT INTO DETALLE_VENTA
                    (id_venta, id_producto, cantidad, precio_unitario)
                    VALUES (%s, %s, %s, %s)""",
                    (id_venta, item["id"],
                     item["cantidad"], item["precio_unitario"]))

                cursor.execute("""
                    UPDATE PRODUCTOS
                    SET stock = stock - %s
                    WHERE id = %s""",
                    (item["cantidad"], item["id"]))

            conn.commit()
            conn.close()
            st.session_state["carrito"] = []
            st.success("✅ Venta registrada. El inventario fue actualizado.")
            st.rerun()

    # ── Historial de ventas ─────────────────────────────────────
    st.divider()
    st.subheader("📋 Historial de ventas")
    conn3 = get_connection()
    df_hist = pd.read_sql("""
        SELECT v.id, v.fecha, v.total, v.metodo_pago,
               GROUP_CONCAT(p.nombre ORDER BY p.nombre SEPARATOR ', ') AS productos
        FROM VENTAS v
        JOIN DETALLE_VENTA dv ON dv.id_venta    = v.id
        JOIN PRODUCTOS     p  ON dv.id_producto  = p.id
        GROUP BY v.id ORDER BY v.fecha DESC LIMIT 50""", conn3)
    conn3.close()
    st.dataframe(df_hist, use_container_width=True)
