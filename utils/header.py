import streamlit as st

def show_header():
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        st.image("assets/logo.png", width=100)  # Logo bên trái
    with col2:
        st.markdown("<h1 style='text-align: center; color: #006400;'>Quầy Thuốc Minh Châu 24h/7</h1>", unsafe_allow_html=True)
    with col3:
        st.image("assets/logo.png", width=100)  # Logo bên phải (dùng cùng file)
    st.markdown("---")