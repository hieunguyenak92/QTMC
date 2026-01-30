import streamlit as st
from utils.sheets import load_df, append_row, update_stock
from utils.header import show_header
from datetime import datetime

show_header()
st.title("📥 Nhập Hàng")

tab1, tab2 = st.tabs(["Nhập sản phẩm mới hoàn toàn", "Nhập thêm sản phẩm hiện có"])

df_sp = load_df("SanPham")

with tab1:
    st.subheader("Nhập sản phẩm mới (tạo mới + nhập hàng)")
    with st.form("NhapSanPhamMoi", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            id_sp = st.text_input("ID sản phẩm (ví dụ: TH001)")
            ten = st.text_input("Tên thuốc*", max_chars=100)
            donvi = st.selectbox("Đơn vị", ["Viên", "Hộp", "Lọ", "Ống", "Chai", "Vỉ"])
        with col2:
            gianhap = st.number_input("Giá nhập (đ)", min_value=0.0)
            giaban = st.number_input("Giá bán (đ)", min_value=0.0)
            sl = st.number_input("Số lượng nhập*", min_value=1)
        
        tongtien = sl * gianhap
        st.write(f"**Thành tiền nhập: {tongtien:,.0f} đ**")
        ghichu = st.text_area("Ghi chú (nhà cung cấp, lô...)")

        submitted = st.form_submit_button("Xác nhận nhập hàng mới")
        if submitted and ten and id_sp:
            append_row("SanPham", [id_sp, ten, donvi, gianhap, giaban, sl, 10, ""])
            append_row("NhapHang", [datetime.now().strftime("%Y-%m-%d"), id_sp, sl, gianhap, tongtien, ghichu])
            st.success(f"Nhập sản phẩm mới {ten} thành công!")
            st.balloons()
            st.rerun()

with tab2:
    st.subheader("Nhập thêm sản phẩm hiện có")
    search = st.text_input("Tìm tên thuốc", key="search_nhap")
    df_filter = df_sp[df_sp["TenThuoc"].str.contains(search, case=False, na=False)] if search else df_sp
    
    options = [f"{row['ID']} - {row['TenThuoc']} (Tồn: {row['TonKho']})" for _, row in df_filter.iterrows()]
    
    with st.form("NhapThem", clear_on_submit=True):
        selected = st.selectbox("Chọn sản phẩm", options)
        if selected:
            id_sp = selected.split(" - ")[0]
            row_sp = df_sp[df_sp["ID"] == id_sp].iloc[0]
            sl = st.number_input("Số lượng nhập", min_value=1)
            dongia = st.number_input("Đơn giá nhập", value=float(row_sp["GiaNhap"]))
            tongtien = sl * dongia
            st.write(f"**Thành tiền: {tongtien:,.0f} đ**")
            ghichu = st.text_input("Ghi chú")

            submitted = st.form_submit_button("Xác nhận nhập")
            if submitted:
                append_row("NhapHang", [datetime.now().strftime("%Y-%m-%d"), id_sp, sl, dongia, tongtien, ghichu])
                update_stock(id_sp, sl)
                st.success(f"Nhập thêm {sl} {row_sp['TenThuoc']} thành công!")
                st.rerun()