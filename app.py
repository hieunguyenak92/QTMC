import streamlit as st
import hashlib

# --- Hàm hash password ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- Hàm kiểm tra đăng nhập ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        with st.form("login_form"):
            st.write("**Đăng nhập hệ thống quản lý nhà thuốc**")
            username = st.text_input("Tên đăng nhập", value="")
            password = st.text_input("Mật khẩu", type="password")
            submitted = st.form_submit_button("Đăng nhập")

            if submitted:
                expected_username = st.secrets["auth"]["username"]
                expected_hash = st.secrets["auth"]["hashed_password"]

                if username == expected_username and make_hashes(password) == expected_hash:
                    st.session_state.authenticated = True
                    st.session_state.username = username  # Lưu username để hiển thị
                    st.rerun()
                else:
                    st.error("Sai tên đăng nhập hoặc mật khẩu")
        return False
    else:
        return True

# --- Main app ---
if check_password():
    st.sidebar.success(f"Chào {st.session_state.username}!")
    if st.sidebar.button("Đăng xuất"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.rerun()

    # Chọn cửa hàng (future-proof)
    cuahang = st.sidebar.selectbox("Cửa hàng", ["MinhChau"], key="cuahang")
    st.sidebar.info(f"Đang quản lý: {cuahang}")

    st.switch_page("pages/1_🏠_Trang_Chủ.py")