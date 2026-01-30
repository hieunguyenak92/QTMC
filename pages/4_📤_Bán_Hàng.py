import streamlit as st
from utils.sheets import load_df, append_row, update_stock
from utils.header import show_header
from datetime import datetime

show_header()
st.title("📤 Bán Hàng")

df_sp = load_df("SanPham")
options = [f"{row['ID']} - {row['TenThuoc']} (Tồn: {row['TonKho']})" for _, row in df_sp.iterrows() if row['TonKho'] > 0]

with st.form("BanHangForm", clear_on_submit=True):
    selected = st.selectbox("Chọn sản phẩm", options or ["Không còn hàng"])
    if not options:
        st.warning("Không còn sản phẩm nào trong tồn kho")
        st.stop()
    id_sp = selected.split(" - ")[0]
    row_sp = df_sp[df_sp["ID"] == id_sp].iloc[0]
    sl_max = int(row_sp["TonKho"])
    sl = st.number_input("Số lượng", min_value=1, max_value=sl_max)
    dongiaban = row_sp["GiaBan"]
    tongtien = sl * dongiaban
    st.write(f"Đơn giá bán: {dongiaban:,.0f} đ → Tổng: {tongtien:,.0f} đ")
    khach = st.text_input("Tên khách (optional)")

    submitted = st.form_submit_button("Xác nhận bán")
    if submitted:
        append_row("BanHang", [datetime.now().strftime("%Y-%m-%d"), id_sp, sl, dongiaban, tongtien, khach])
        update_stock(id_sp, -sl)
        st.success(f"Bán thành công! Thu {tongtien:,.0f} đ")
        st.balloons()
        st.rerun()