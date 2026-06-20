import streamlit as st
import pandas as pd
from modulos.config.conexion import get_connection

def mostrar():
    st.title("🚚 Proveedores")
    conn = get_connection()
    if conn is None:
        st.error("Error de conexión."); return

    df = pd.read_sql("SELECT * FROM PROVEEDORES", conn)
    st.dataframe(df, use_container_width=True)
    st.caption(f"{len(df)} proveedor(es) registrado(s)")

    st.divider()
    st.subheader("➕ Registrar proveedor")
    c1, c2 = st.columns(2)
    with c1:
        empresa   = st.text_input("Empresa / Razón social")
        direccion = st.text_input("Dirección física")
        telefono  = st.text_input("Teléfono de contacto")
    with c2:
        vendedor  = st.text_input("Nombre del vendedor / asesor")
        nit       = st.text_input("NIT (opcional)")
        nrc       = st.text_input("NRC (opcional)")

    if st.button("💾 Guardar proveedor", use_container_width=True):
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO PROVEEDORES
            (empresa, direccion, telefono, vendedor, nit, nrc)
            VALUES (%s,%s,%s,%s,%s,%s)""",
            (empresa, direccion, telefono, vendedor, nit, nrc))
        conn.commit(); conn.close()
        st.success("✅ Proveedor guardado.")
        st.rerun()
