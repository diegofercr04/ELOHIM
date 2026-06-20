import streamlit as st
import pandas as pd
from modulos.config.conexion import get_connection

def mostrar(rol):
    st.title("📦 Inventario de Productos")
    conn = get_connection()
    if conn is None:
        st.error("Error de conexión."); return

    df = pd.read_sql("SELECT * FROM PRODUCTOS", conn)

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
        categorias = ["Todas"] + df["categoria"].unique().tolist()
        cat_sel = st.selectbox("Categoría", categorias)
    with col3:
        ubicaciones = ["Todas"] + df["ubicacion"].unique().tolist()
        ubi_sel = st.selectbox("Ubicación", ubicaciones)

    if busqueda:
        df = df[df["nombre"].str.contains(busqueda, case=False)]
    if cat_sel != "Todas":
        df = df[df["categoria"] == cat_sel]
    if ubi_sel != "Todas":
        df = df[df["ubicacion"] == ubi_sel]

    st.dataframe(df, use_container_width=True)
    st.caption(f"{len(df)} producto(s) encontrado(s)")

    # ── Insertar producto (solo admin) ───────────────────────────
    if rol == "admin":
        st.divider()
        st.subheader("➕ Agregar nuevo producto")
        c1, c2 = st.columns(2)
        with c1:
            nombre     = st.text_input("Nombre del producto")
            categoria  = st.selectbox("Categoría", [
                "Construcción", "Fontanería", "Electricidad",
                "Pinturas", "Automotriz", "Herramientas", "Carpintería"])
            precio_costo  = st.number_input("Precio de costo ($)", min_value=0.0, format="%.2f")
            precio_venta  = st.number_input("Precio de venta ($)", min_value=0.0, format="%.2f")
        with c2:
            stock        = st.number_input("Stock actual", min_value=0, step=1)
            stock_minimo = st.number_input("Stock mínimo (alerta)", min_value=0, step=1)
            ubicacion    = st.selectbox("Ubicación física", [
                "Bodega interna", "Área abierta / patio", "Mostrador"])
            tiene_barcode = st.checkbox("¿Tiene código de barras?", value=True)
            codigo_barras = st.text_input("Código de barras") if tiene_barcode else ""

        if st.button("💾 Guardar producto", use_container_width=True):
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO PRODUCTOS
                (nombre, categoria, precio_costo, precio_venta,
                 stock, stock_minimo, ubicacion, codigo_barras)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (nombre, categoria, precio_costo, precio_venta,
                 stock, stock_minimo, ubicacion, codigo_barras))
            conn.commit(); conn.close()
            st.success("✅ Producto guardado.")
            st.rerun()
