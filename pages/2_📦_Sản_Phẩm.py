import streamlit as st
from utils.sheets import load_df, append_row
from utils.header import show_header

show_header()
st.title("📦 Quản Lý Sản Phẩm")

tab1, tab2 = st.tabs(["Danh sách", "Thêm mới"])

with tab1:
    df = load_df("SanPham")
    df_edit = st.data_editor(
        df,
        num_rows="dynamic",
        column_config={
            "TonKho": st.column_config.NumberColumn(disabled=True),
            "HanSuDung": st.column_config.DateColumn(format="DD/MM/YYYY")
        }
    )

with tab2:
    with st.form("ThemSanPham"):
        id_sp = st.text_input("ID sản phẩm (mã riêng, ví dụ: THUOC001)")
        ten = st.text_input("Tên thuốc*")
        donvi = st.selectbox("Đơn vị", ["Viên", "Hộp", "Lọ", "Ống", "Chai", "Vỉ"])
        gianhap = st.number_input("Giá nhập", min_value=0.0)
        giaban = st.number_input("Giá bán", min_value=0.0)
        tontoithieu = st.number_input("Tồn tối thiểu cảnh báo", value=10)
        hansd = st.date_input("Hạn sử dụng (nếu có)", required=False)
        submitted = st.form_submit_button("Thêm sản phẩm")
        if submitted and ten:
            hansd_str = str(hansd) if hansd else ""
            append_row("SanPham", [id_sp, ten, donvi, gianhap, giaban, 0, tontoithieu, hansd_str])
            st.success("Thêm thành công!")
            st.rerun()