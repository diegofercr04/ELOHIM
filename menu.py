import streamlit as st
from modulos import inventario, proveedores, reportes, caja, compras, ventas

def mostrar_menu():
    rol = st.session_state.get("rol", "vendedor")

    st.sidebar.image("https://via.placeholder.com/280x60/185FA5/FFFFFF?text=ELOHIM")
    st.sidebar.markdown(f"**👤 {st.session_state['usuario']}** — `{rol}`")
    st.sidebar.divider()

    opciones_admin = [
        "📦 Inventario",
        "🧾 Ventas",
        "🛒 Compras",
        "🚚 Proveedores",
        "📊 Reportes",
        "💰 Arqueo de Caja"
    ]
    opciones_vendedor = ["📦 Inventario", "🧾 Ventas"]

    opciones = opciones_admin if rol == "admin" else opciones_vendedor
    opcion   = st.sidebar.radio("Navegación", opciones)
    st.sidebar.divider()

    if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["carrito"]     = []
        st.rerun()

    if   opcion == "📦 Inventario":     inventario.mostrar(rol)
    elif opcion == "🧾 Ventas":         ventas.mostrar()
    elif opcion == "🛒 Compras":        compras.mostrar()
    elif opcion == "🚚 Proveedores":    proveedores.mostrar()
    elif opcion == "📊 Reportes":       reportes.mostrar()
    elif opcion == "💰 Arqueo de Caja": caja.mostrar()
