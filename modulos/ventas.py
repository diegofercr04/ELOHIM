import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from modulos.config.conexion import get_connection
from modulos.factura import generar_factura_pdf

# Agregar esta línea justo después de los imports
SV_TZ = pytz.timezone("America/El_Salvador")

try:
    from streamlit_qrcode_scanner import qrcode_scanner
    SCANNER_DISPONIBLE = True
except ImportError:
    SCANNER_DISPONIBLE = False


def _agregar_al_carrito(prod, cantidad, descuento_pct=0):
    precio_original = float(prod["precio_venta"])
    precio_con_desc = precio_original * (1 - descuento_pct / 100)

    for item in st.session_state["carrito"]:
        if item["id"] == int(prod["id"]) and item["descuento_pct"] == descuento_pct:
            item["cantidad"] += cantidad
            return
    st.session_state["carrito"].append({
        "id":              int(prod["id"]),
        "nombre":          prod["nombre"],
        "precio_original": precio_original,
        "precio_unitario": precio_con_desc,   # precio ya con descuento
        "descuento_pct":   descuento_pct,
        "cantidad":        cantidad,
    })


def mostrar():
    st.title("🧾 Registro de Ventas")

    if "carrito" not in st.session_state:
        st.session_state["carrito"] = []
    if "ultima_factura" not in st.session_state:
        st.session_state["ultima_factura"] = None

    conn = get_connection()
    if conn is None:
        st.error("Error de conexión.")
        return

    df_prod = pd.read_sql(
        "SELECT id, nombre, precio_venta, stock, codigo_barras FROM PRODUCTOS WHERE stock > 0 ORDER BY nombre",
        conn
    )

    # ── Factura lista para descargar ────────────────────────────
    if st.session_state["ultima_factura"] is not None:
        st.success("✅ Venta registrada exitosamente.")
        st.download_button(
            label="📄 Descargar factura PDF",
            data=st.session_state["ultima_factura"],
            file_name=f"factura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        if st.button("🆕 Nueva venta", use_container_width=True):
            st.session_state["ultima_factura"] = None
            st.rerun()
        return

    # ── Tabs escáner / manual ───────────────────────────────────
    tab_scan, tab_manual = st.tabs([
        "📷 Escanear código de barras",
        "🔍 Buscar manualmente"
    ])

    with tab_scan:
        if not SCANNER_DISPONIBLE:
            st.warning("Librería de escáner no instalada.")
        else:
            st.caption("Apunta la cámara al código de barras del producto.")
            codigo_escaneado = qrcode_scanner(key="scanner_ventas")
            if codigo_escaneado:
                resultado = df_prod[df_prod["codigo_barras"] == codigo_escaneado]
                if resultado.empty:
                    st.error(f"❌ Código '{codigo_escaneado}' no encontrado.")
                else:
                    prod = resultado.iloc[0]
                    st.info(f"✅ Producto: **{prod['nombre']}** — ${prod['precio_venta']:.2f}")
                    cant_scan = st.number_input(
                        "Cantidad", min_value=1,
                        max_value=int(prod["stock"]),
                        step=1, key="cant_scan"
                    )
                    if st.button("🛒 Agregar al carrito", key="add_scan"):
                        _agregar_al_carrito(prod, cant_scan)
                        st.rerun()

    with tab_manual:
        if df_prod.empty:
            st.warning("⚠️ No hay productos con stock disponible.")
        else:
            c_cod, c_nom = st.columns([1, 2])
            with c_cod:
                codigo_manual = st.text_input(
                    "🔢 Código de barras",
                    placeholder="Digita el código...",
                    key="cod_manual"
                )
            with c_nom:
                busqueda = st.text_input(
                    "🔍 O buscar por nombre",
                    key="busq_manual",
                    disabled=bool(codigo_manual)
                )

            if codigo_manual:
                df_filtrado = df_prod[df_prod["codigo_barras"] == codigo_manual]
                if df_filtrado.empty:
                    st.error(f"❌ Código '{codigo_manual}' no encontrado.")
                else:
                    st.success(f"✅ Producto: **{df_filtrado.iloc[0]['nombre']}**")
                    df_filtrado = df_filtrado
            elif busqueda:
                df_filtrado = df_prod[
                    df_prod["nombre"].str.contains(busqueda, case=False)
                ]
            else:
                df_filtrado = df_prod

            prod_map = {
                f"{r['nombre']}  —  ${r['precio_venta']:.2f}  (stock: {r['stock']})": r
                for _, r in df_filtrado.iterrows()
            }
            if prod_map:
                prod_sel  = st.selectbox("Producto", list(prod_map.keys()),
                                          key="prod_manual")
                prod_info = prod_map[prod_sel]
                cant_man  = st.number_input(
                    "Cantidad", min_value=1,
                    max_value=int(prod_info["stock"]),
                    step=1, key="cant_manual"
                )
                 descuento_item = st.number_input(
                "% Descuento (0 = sin descuento)",
                min_value=0, max_value=100,
                step=1, value=0,
                key="desc_manual"
            )

            # Mostrar precio resultante en tiempo real
            precio_base = float(prod_info["precio_venta"])
            if descuento_item > 0:
                precio_final = precio_base * (1 - descuento_item / 100)
                st.info(
                    f"Precio normal: ~~${precio_base:.2f}~~  →  "
                    f"Con {descuento_item}% desc: **${precio_final:.2f}**"
                )

            if st.button("🛒 Agregar al carrito", key="add_manual"):
                _agregar_al_carrito(prod_info, cant_man, descuento_item)
                st.rerun()

# ── En tab_scan, mismo patrón ───────────────────────────────────
                    descuento_scan = st.number_input(
                        "% Descuento (0 = sin descuento)",
                        min_value=0, max_value=100,
                        step=1, value=0,
                        key="desc_scan"
                    )
                    if descuento_scan > 0:
                        precio_final_s = float(prod["precio_venta"]) * (1 - descuento_scan / 100)
                        st.info(
                            f"Precio normal: ~~${float(prod['precio_venta']):.2f}~~  →  "
                            f"Con {descuento_scan}% desc: **${precio_final_s:.2f}**"
                        )
                    if st.button("🛒 Agregar al carrito", key="add_scan"):
                        _agregar_al_carrito(prod, cant_scan, descuento_scan)
                        st.rerun()

    # ── Carrito ─────────────────────────────────────────────────
    st.divider()
    st.subheader("🛒 Carrito actual")

    if not st.session_state["carrito"]:
        st.info("El carrito está vacío.")
    else:
        for i, item in enumerate(st.session_state["carrito"]):
            subtotal_item = item["cantidad"] * item["precio_unitario"]
            c_nom, c_qty, c_sub, c_del = st.columns([4, 3, 2, 1])

            c_nom.write(item["nombre"])

            # Mostrar precio con descuento si aplica
            if item["descuento_pct"] > 0:
                c_qty.markdown(
                    f"{item['cantidad']} × ~~${item['precio_original']:.2f}~~ "
                    f"**${item['precio_unitario']:.2f}** (-{item['descuento_pct']}%)"
                )
            else:
                c_qty.write(f"{item['cantidad']} × ${item['precio_unitario']:.2f}")

            c_sub.write(f"**${subtotal_item:.2f}**")

            if c_del.button("✕", key=f"del_{i}"):
                st.session_state["carrito"].pop(i)
                st.rerun()

        # Total sumando los precios ya con descuento de cada producto
        total_venta = sum(
            x["cantidad"] * x["precio_unitario"]
            for x in st.session_state["carrito"]
        )
        st.metric("Total", f"${total_venta:.2f}")

        if st.button("🗑️ Vaciar carrito"):
            st.session_state["carrito"] = []
            st.rerun()

      st.divider()
        st.subheader("✅ Confirmar venta")
        c1, c2, c3 = st.columns(3)
        metodo_pago = c1.radio(
            "Método de pago", ["efectivo", "transferencia"], horizontal=True
        )
        fecha_v = c2.date_input("Fecha", value=datetime.today())
        hora_v  = c3.time_input("Hora", value=datetime.now(SV_TZ).time().replace(tzinfo=None))

        # El total ya tiene los descuentos individuales aplicados
        total_final = sum(
            x["cantidad"] * x["precio_unitario"]
            for x in st.session_state["carrito"]
        )
        st.success(f"💵 Total a cobrar: **${total_final:.2f}** — Pago en **{metodo_pago}**")

        if st.button("✅ Confirmar y registrar venta",
                     use_container_width=True, type="primary"):
            fecha_hora = SV_TZ.localize(datetime.combine(fecha_v, hora_v))
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO VENTAS (fecha, total, metodo_pago, usuario_id) VALUES (%s,%s,%s,%s)",
                (fecha_hora, total_final, metodo_pago, st.session_state.get("usuario_id"))
            )
            id_venta = cursor.lastrowid
            items_factura = []
            for item in st.session_state["carrito"]:
                cursor.execute(
                    "INSERT INTO DETALLE_VENTA (id_venta,id_producto,cantidad,precio_unitario) VALUES (%s,%s,%s,%s)",
                    (id_venta, item["id"], item["cantidad"], item["precio_unitario"])
                )
                cursor.execute(
                    "UPDATE PRODUCTOS SET stock = stock - %s WHERE id = %s",
                    (item["cantidad"], item["id"])
                )
                items_factura.append(item)
            conn.commit()
            conn.close()
            pdf_bytes = generar_factura_pdf(
                id_venta    = id_venta,
                items       = items_factura,
                total       = total_final,
                descuento   = 0,
                metodo_pago = metodo_pago,
                fecha_hora  = fecha_hora,
                vendedor    = st.session_state.get("usuario", "")
            )
            st.session_state["carrito"]        = []
            st.session_state["ultima_factura"] = pdf_bytes
            st.rerun()

   # ── Historial ────────────────────────────────────────────────
    st.divider()
    st.subheader("📋 Últimas 50 ventas")
    conn2 = get_connection()
    df_hist = pd.read_sql("""
        SELECT v.id, v.fecha, v.total, v.metodo_pago,
               GROUP_CONCAT(p.nombre SEPARATOR ', ') AS productos
        FROM VENTAS v
        JOIN DETALLE_VENTA dv ON dv.id_venta   = v.id
        JOIN PRODUCTOS     p  ON dv.id_producto = p.id
        GROUP BY v.id
        ORDER BY v.fecha DESC
        LIMIT 50""", conn2)
    conn2.close()
    st.dataframe(df_hist, use_container_width=True)

     # ── Cancelar venta (solo admin) ──────────────────────────────
    st.divider()
    rol = st.session_state.get("rol", "vendedor")

    if rol != "admin":
        st.caption("🔒 La cancelación de ventas es exclusiva del administrador.")
    else:
        st.subheader("❌ Cancelar una venta")
        st.warning("⚠️ Al cancelar una venta se devolverá el stock de todos sus productos.")

        conn_c = get_connection()
        df_cancel = pd.read_sql("""
            SELECT v.id, v.fecha, v.total, v.metodo_pago,
                   GROUP_CONCAT(p.nombre SEPARATOR ', ') AS productos
            FROM VENTAS v
            JOIN DETALLE_VENTA dv ON dv.id_venta   = v.id
            JOIN PRODUCTOS     p  ON dv.id_producto = p.id
            GROUP BY v.id
            ORDER BY v.fecha DESC
            LIMIT 50""", conn_c)

        if df_cancel.empty:
            st.info("No hay ventas registradas.")
            conn_c.close()
        else:
            venta_map = {
                f"Venta #{row['id']} — {row['fecha']} — ${row['total']:.2f} — {row['productos']}": row["id"]
                for _, row in df_cancel.iterrows()
            }
            venta_sel    = st.selectbox("Seleccionar venta a cancelar",
                                         list(venta_map.keys()), key="cancel_venta_sel")
            id_venta_sel = venta_map[venta_sel]

            confirmar_v = st.checkbox(
                "Confirmo que quiero cancelar esta venta y devolver el stock",
                key="confirmar_cancel_venta"
            )
            if confirmar_v:
                if st.button("❌ Cancelar venta", use_container_width=True,
                             key="btn_cancel_venta"):
                    _cancelar_venta(id_venta_sel, conn_c)
            conn_c.close()


# ── Función fuera de mostrar() ───────────────────────────────
def _cancelar_venta(id_venta, conn):
    """Devuelve el stock y elimina la venta con todo su detalle."""
    cur = conn.cursor(dictionary=True)

    # 1. Obtener todos los productos de la venta
    cur.execute(
        "SELECT id_producto, cantidad FROM DETALLE_VENTA WHERE id_venta = %s",
        (id_venta,)
    )
    items = cur.fetchall()

    # 2. Devolver stock de cada producto
    for item in items:
        cur.execute(
            "UPDATE PRODUCTOS SET stock = stock + %s WHERE id = %s",
            (item["cantidad"], item["id_producto"])
        )

    # 3. Eliminar detalle y luego la venta
    cur.execute("DELETE FROM DETALLE_VENTA WHERE id_venta = %s", (id_venta,))
    cur.execute("DELETE FROM VENTAS WHERE id = %s", (id_venta,))

    conn.commit()
    conn.close()
    st.success("✅ Venta cancelada. El stock fue devuelto al inventario.")
    st.rerun()
