import streamlit as st
from login import login
from menu  import mostrar_menu

st.set_page_config(
    page_title = "Ferretería Elohim",
    page_icon  = "🔩",
    layout     = "wide"
)

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if st.session_state["autenticado"]:
    mostrar_menu()
else:
    login()
