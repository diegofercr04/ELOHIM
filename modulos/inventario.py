import streamlit as st
import pandas as pd
from modulos.config.conexion import get_connection

CATEGORIAS_BASE = [
    "Construcción", "Fontanería", "Electricidad",
    "Pinturas", "Automotriz", "Herramientas", "Carpintería", "Otra"
]
UBICACIONES_BASE = ["Bodega interna", "Área abierta / patio", "Mostrador", "Otra"]


def mostrar(rol):
    st.title("📦 Inventario de Productos")
    conn = get_connection()
    if conn is None:
        st.error("Error de conexión."); return

    df = pd.read_sql("SELECT * FROM PRODUCTOS ORDER BY nombre", conn)

    # ── Alertas de stock mínimo ──────────────────────────────────
    bajos = df[df["stock"] <= df["stock_minimo"]]
    if not bajos.empty:
        st.warning(f"⚠️ {len(bajos)} producto(s) por debajo del stock mínimo:")
        st.dataframe(bajos[["nombre", "stock", "stock_minimo", "ubicacion"]],
                    use_container_width=True)
        st.divider()

    # ── Filtros ───────────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        busqueda = st.text_input("🔍 Buscar producto")
    with col2:
        cats_bd  = df["categoria"].dropna().unique().tolist()
        cats_fil = ["Todas"] + sorted(set(cats_bd))
        cat_sel  = st.selectbox("Categoría", cats_fil)
    with col3:
        ubis_bd  = df["ubicacion"].dropna().unique().tolist()
        ubis_fil = ["Todas"] + sorted(set(ubis_bd))
        ubi_sel  = st.selectbox("Ubicación", ubis_fil)

    df_vis = df.copy()
    if busqueda:
        df_vis = df_vis[df_vis["nombre"].str.contains(busqueda, case=False)]
    if cat_sel != "Todas":
        df_vis = df_vis[df_vis["categoria"] == cat_sel]
    if ubi_sel != "Todas":
        df_vis = df_vis[df_vis["ubicacion"] == ubi_sel]

    st.dataframe(df_vis, use_container_width=True)
    st.caption(f"{len(df_vis)} producto(s) encontrado(s)")

    # ── Solo admin puede agregar y editar ────────────────────────
    if rol != "admin":
        return

    st.divider()

     # ── Tabs: Agregar / Editar / Eliminar ───────────────────────
    tab_add, tab_edit, tab_del = st.tabs([
        "➕ Agregar producto",
        "✏️ Editar producto",
        "🗑️ Eliminar producto"
    ])

    with tab_add:
        _form_agregar(conn, df, cats_bd, ubis_bd)

    with tab_edit:
        _form_editar(conn, df, cats_bd, ubis_bd)

    with tab_del:
        _form_eliminar(conn, df)

    conn.close()

def _selector_categoria(cats_bd, key_sel, key_nueva):
    """Selectbox de categoría con opción 'Otra' para crear nueva."""
    cats_disponibles = sorted(set(CATEGORIAS_BASE + cats_bd))
    cat_sel = st.selectbox("Categoría", cats_disponibles, key=key_sel)
    if cat_sel == "Otra":
        cat_sel = st.text_input("Nueva categoría", key=key_nueva)
    return cat_sel


def _selector_ubicacion(ubis_bd, key_sel, key_nueva):
    """Selectbox de ubicación con opción 'Otra' para crear nueva."""
    ubis_disponibles = sorted(set(UBICACIONES_BASE + ubis_bd))
    ubi_sel = st.selectbox("Ubicación física", ubis_disponibles, key=key_sel)
    if ubi_sel == "Otra":
        ubi_sel = st.text_input("Nueva ubicación", key=key_nueva)
    return ubi_sel


def _form_agregar(conn, df, cats_bd, ubis_bd):
    c1, c2 = st.columns(2)
    with c1:
        nombre       = st.text_input("Nombre del producto", key="add_nombre")
        categoria    = _selector_categoria(cats_bd, "add_cat", "add_cat_nueva")
        precio_costo = st.number_input("Precio de costo ($)", min_value=0.0,
                                        format="%.2f", key="add_costo")
        precio_venta = st.number_input("Precio de venta ($)", min_value=0.0,
                                        format="%.2f", key="add_venta")
    with c2:
        stock        = st.number_input("Stock inicial", min_value=0,
                                       step=1, key="add_stock")
        stock_minimo = st.number_input("Stock mínimo (alerta)", min_value=0,
                                       step=1, key="add_stockmin")
        ubicacion    = _selector_ubicacion(ubis_bd, "add_ubi", "add_ubi_nueva")
        tiene_barcode = st.checkbox("¿Tiene código de barras?", value=True, key="add_cb")
        codigo_barras = st.text_input("Código de barras", key="add_cod") if tiene_barcode else ""
        

    if st.button("💾 Guardar producto", use_container_width=True, key="btn_add"):
        if not nombre:
            st.error("El nombre del producto es obligatorio."); return
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO PRODUCTOS
            (nombre, categoria, precio_costo, precio_venta,
             stock, stock_minimo, ubicacion, codigo_barras)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (nombre, categoria, precio_costo, precio_venta,
             stock, stock_minimo, ubicacion, codigo_barras))
        conn.commit()
        st.success("✅ Producto guardado.")
        st.rerun()


def _form_editar(conn, df, cats_bd, ubis_bd):
    if df.empty:
        st.info("No hay productos registrados aún.")
        return

    prod_map = {
        f"{r['nombre']} — {r['categoria']}": r
        for _, r in df.iterrows()
    }

    prod_sel = st.selectbox(
        "Seleccionar producto a editar",
        list(prod_map.keys()),
        key="edit_sel"
    )
    prod = prod_map[prod_sel]

    # Detectar si cambió el producto seleccionado
    if st.session_state.get("edit_prod_anterior") != prod_sel:
        st.session_state["edit_prod_anterior"] = prod_sel
        # Cargar los valores del producto recién seleccionado
        st.session_state["edit_nom"]      = prod["nombre"]
        st.session_state["edit_costo"]    = float(prod["precio_costo"] or 0)
        st.session_state["edit_venta"]    = float(prod["precio_venta"] or 0)
        st.session_state["edit_stock"]    = int(prod["stock"])
        st.session_state["edit_stockmin"] = int(prod["stock_minimo"])
        st.session_state["edit_cod"]      = prod["codigo_barras"] or ""
        st.rerun()

    st.markdown(f"Editando: **{prod['nombre']}**")
    c1, c2 = st.columns(2)
    with c1:
        nombre_e = st.text_input("Nombre", key="edit_nom")

        cats_disp = sorted(set(CATEGORIAS_BASE + cats_bd))
        cat_idx   = cats_disp.index(prod["categoria"]) if prod["categoria"] in cats_disp else 0
        cat_e     = st.selectbox("Categoría", cats_disp, index=cat_idx, key="edit_cat")
        if cat_e == "Otra":
            cat_e = st.text_input("Nueva categoría", key="edit_cat_nueva")

        precio_costo_e = st.number_input("Precio de costo ($)",
                                          min_value=0.0, format="%.2f",
                                          key="edit_costo")
        precio_venta_e = st.number_input("Precio de venta ($)",
                                          min_value=0.0, format="%.2f",
                                          key="edit_venta")
    with c2:
        stock_e    = st.number_input("Stock actual", min_value=0, step=1,
                                     key="edit_stock")
        stockmin_e = st.number_input("Stock mínimo", min_value=0, step=1,
                                     key="edit_stockmin")

        ubis_disp = sorted(set(UBICACIONES_BASE + ubis_bd))
        ubi_idx   = ubis_disp.index(prod["ubicacion"]) if prod["ubicacion"] in ubis_disp else 0
        ubi_e     = st.selectbox("Ubicación", ubis_disp, index=ubi_idx, key="edit_ubi")
        if ubi_e == "Otra":
            ubi_e = st.text_input("Nueva ubicación", key="edit_ubi_nueva")

        cod_e = st.text_input("Código de barras", key="edit_cod")

    if st.button("💾 Guardar cambios", use_container_width=True,
                 type="primary", key="btn_edit"):
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE PRODUCTOS SET
                nombre        = %s,
                categoria     = %s,
                precio_costo  = %s,
                precio_venta  = %s,
                stock         = %s,
                stock_minimo  = %s,
                ubicacion     = %s,
                codigo_barras = %s
            WHERE id = %s""",
            (nombre_e, cat_e, precio_costo_e, precio_venta_e,
             stock_e, stockmin_e, ubi_e, cod_e, int(prod["id"])))
        conn.commit()
        st.success("✅ Producto actualizado correctamente.")
        st.rerun()

def _form_eliminar(conn, df):
    if df.empty:
        st.info("No hay productos registrados aún.")
        return

    st.warning("⚠️ Esta acción es permanente y no se puede deshacer.")

    prod_map = {
        f"{r['nombre']} — {r['categoria']} (stock: {r['stock']})": r
        for _, r in df.iterrows()
    }
    prod_sel = st.selectbox(
        "Seleccionar producto a eliminar",
        list(prod_map.keys()),
        key="del_sel"
    )
    prod = prod_map[prod_sel]

    # Mostrar datos del producto seleccionado
    st.markdown(
        f"**Nombre:** {prod['nombre']}  \n"
        f"**Categoría:** {prod['categoria']}  \n"
        f"**Precio venta:** ${prod['precio_venta']:.2f}  \n"
        f"**Stock actual:** {prod['stock']} unidades  \n"
        f"**Ubicación:** {prod['ubicacion']}"
    )

    # Confirmación con checkbox para evitar eliminaciones accidentales
    confirmar = st.checkbox(
        f"Confirmo que quiero eliminar **{prod['nombre']}** permanentemente",
        key="del_confirmar"
    )

    if confirmar:
        if st.button("🗑️ Eliminar producto", use_container_width=True,
                     key="btn_eliminar"):
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM PRODUCTOS WHERE id = %s",
                    (int(prod["id"]),)
                )
                conn.commit()
                st.success(f"✅ Producto '{prod['nombre']}' eliminado correctamente.")
                st.rerun()
            except Exception:
                st.error(
                    "❌ No se puede eliminar este producto porque tiene ventas o compras "
                    "registradas. Si ya no lo vendes puedes dejar el stock en 0."
                )
