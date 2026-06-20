import streamlit as st
from modulos import inventario, proveedores, reportes, caja

def mostrar_menu():
    rol = st.session_state.get("rol", "vendedor")

    st.sidebar.image("https://via.placeholder.com/280x60/185FA5/FFFFFF?text=ELOHIM")
    st.sidebar.markdown(f"**👤 {st.session_state['usuario']}** — `{rol}`")
    st.sidebar.divider()

    # Opciones disponibles según rol
    opciones_admin    = ["📦 Inventario", "🚚 Proveedores",
                         "📊 Reportes", "💰 Arqueo de Caja"]
    opciones_vendedor = ["📦 Inventario"]

    opciones = opciones_admin if rol == "admin" else opciones_vendedor

    opcion = st.sidebar.radio("Navegación", opciones)
    st.sidebar.divider()

    if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()

    if   opcion == "📦 Inventario":     inventario.mostrar(rol)
    elif opcion == "🚚 Proveedores":    proveedores.mostrar()
    elif opcion == "📊 Reportes":       reportes.mostrar()
    elif opcion == "💰 Arqueo de Caja": caja.mostrar()
