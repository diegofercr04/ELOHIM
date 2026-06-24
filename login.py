import streamlit as st
from modulos.config.conexion import get_connection


def login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔩 Ferretería Elohim")
        st.markdown("### Iniciar sesión")
        usuario    = st.text_input("Usuario")
        contrasena = st.text_input("Contraseña", type="password")

        if st.button("Entrar", use_container_width=True):
            conn = get_connection()
            if conn is None:
                st.error("❌ Error de conexión con la base de datos.")
                return
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM USUARIO WHERE usuario=%s AND contrasena=%s",
                (usuario, contrasena)
            )
            user = cursor.fetchone()
            conn.close()

            if user:
                st.session_state["autenticado"] = True
                st.session_state["usuario"]     = user["usuario"]
                st.session_state["rol"]         = user["rol"]
                st.session_state["usuario_id"]  = user["id"]
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos.")
