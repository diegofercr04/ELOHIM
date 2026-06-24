import streamlit as st
import pandas as pd
from datetime import datetime
from modulos.config.conexion import get_connection
from modulos.config.utils import safe_rerun
from modulos.factura import generar_factura_pdf

try:
    from streamlit_qrcode_scanner import qrcode_scanner
    SCANNER_DISPONIBLE = True
except ImportError:
    SCANNER_DISPONIBLE = False


def _agregar_al_carrito(prod, cantidad):
    for item in st.session_state["carrito"]:
        if item["id"] == int(prod["id"]):
            item["cantidad"] += cantidad
            return
    st.session_state["carrito"].append({
        "id": int(prod["id"]),
        "nombre": prod["nombre"],
        "precio_unitario": float(prod["precio_venta"]),
        "cantidad": cantidad,
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

    # ── Botón descarga si hay factura reciente ──────────────────
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
            safe_rerun()
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
                        "Cantidad",
                        min_value=1,
                        max_value=int(prod["stock"]),
                        step=1,
                        key="cant_scan"
                    )
                    if st.button("🛒 Agregar al carrito", key="add_scan"):
                        _agregar_al_carrito(prod, cant_scan)
                        safe_rerun()

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
                    st.success(f"✅ Producto encontrado: **{df_filtrado.iloc[0]['nombre']}**")
            elif busqueda:
                df_filtrado = df_prod[df_prod["nombre"].str.contains(busqueda, case=False)]
            else:
                df_filtrado = df_prod

            prod_map = {
                f"{r['nombre']}  —  ${r['precio_venta']:.2f}  (stock: {r['stock']})": r
                for _, r in df_filtrado.iterrows()
            }
            if prod_map:
                prod_sel = st.selectbox("Producto", list(prod_map.keys()), key="prod_manual")
                prod_info = prod_map[prod_sel]
                cant_man = st.number_input(
                    "Cantidad",
                    min_value=1,
                    max_value=int(prod_info["stock"]),
                    step=1,
                    key="cant_manual"
                )
                if st.button("🛒 Agregar al carrito", key="add_manual"):
                    _agregar_al_carrito(prod_info, cant_man)
                    safe_rerun()

    # ── Carrito ─────────────────────────────────────────────────
    st.divider()
    st.subheader("🛒 Carrito actual")

    if not st.session_state["carrito"]:
        st.info("El carrito está vacío.")
    else:
        for i, item in enumerate(st.session_state["carrito"]):
            subtotal = item["cantidad"] * item["precio_unitario"]
            c_nom, c_qty, c_sub, c_del = st.columns([4, 2, 2, 1])
            c_nom.write(item["nombre"])
            c_qty.write(f"{item['cantidad']} × ${item['precio_unitario']:.2f}")
            c_sub.write(f"**${subtotal:.2f}**")
            if c_del.button("✕", key=f"del_{i}"):
                st.session_state["carrito"].pop(i)
                safe_rerun()

        total_venta = sum(
            x["cantidad"] * x["precio_unitario"]
            for x in st.session_state["carrito"]
        )
        st.metric("Total", f"${total_venta:.2f}")

        if st.button("🗑️ Vaciar carrito"):
            st.session_state["carrito"] = []
            safe_rerun()

        # ── Confirmar venta ──────────────────────────────────────────
        st.divider()
        st.subheader("✅ Confirmar venta")
        c1, c2, c3 = st.columns(3)
        metodo_pago = c1.radio(
            "Método de pago", ["efectivo", "transferencia"], horizontal=True
        )
        fecha_v = c2.date_input("Fecha", value=datetime.today())
        hora_v  = c3.time_input("Hora", value=datetime.now().time())

        if st.button("✅ Confirmar y registrar venta", use_container_width=True, type="primary"):
            fecha_hora = datetime.combine(fecha_v, hora_v)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO VENTAS (fecha, total, metodo_pago, usuario_id) VALUES (%s,%s,%s,%s)",
                (fecha_hora, total_venta, metodo_pago, st.session_state.get("usuario_id"))
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
                id_venta=id_venta,
                items=items_factura,
                total=total_venta,
                metodo_pago=metodo_pago,
                fecha_hora=fecha_hora,
                vendedor=st.session_state.get("usuario", "")
            )
            st.session_state["carrito"] = []
            st.session_state["ultima_factura"] = pdf_bytes
            safe_rerun()

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
