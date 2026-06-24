import streamlit as st
from modulos import inventario, proveedores, reportes, caja, compras, ventas


def mostrar_menu():
    rol = st.session_state.get("rol", "vendedor")
    st.sidebar.markdown(
        f"**👤 {st.session_state['usuario']}** — `{rol}`"
    )
    st.sidebar.divider()

    opciones_admin = [
        "🧾 Ventas",
        "🛒 Compras",
        "📦 Inventario",
        "🚚 Proveedores",
        "📊 Reportes",
        "💰 Arqueo de Caja",
    ]
    opciones_vendedor = ["🧾 Ventas", "📦 Inventario"]

    opciones = opciones_admin if rol == "admin" else opciones_vendedor
    opcion   = st.sidebar.radio("Navegación", opciones)
    st.sidebar.divider()

    if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["carrito"]     = []
        safe_rerun()

    if   opcion == "🧾 Ventas":         ventas.mostrar()
    elif opcion == "🛒 Compras":        compras.mostrar()
    elif opcion == "📦 Inventario":     inventario.mostrar(rol)
    elif opcion == "🚚 Proveedores":    proveedores.mostrar()
    elif opcion == "📊 Reportes":       reportes.mostrar()
    elif opcion == "💰 Arqueo de Caja": caja.mostrar()
