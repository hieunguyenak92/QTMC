import streamlit as st
from utils.sheets import load_df
from utils.header import show_header

show_header()
st.title("🏠 Trang Chủ - Quản Lý Nhà Thuốc")

col1, col2, col3, col4 = st.columns(4)
df_sp = load_df("SanPham")
df_nhap = load_df("NhapHang")
df_ban = load_df("BanHang")

tong_sp = len(df_sp)
tonkho = df_sp["TonKho"].sum()
doanhthu = df_ban["TongTienBan"].sum() if not df_ban.empty else 0
loinhuan = doanhthu - (df_nhap["TongTienNhap"].sum() if not df_nhap.empty else 0)

col1.metric("Tổng sản phẩm", tong_sp)
col2.metric("Tồn kho", f"{tonkho:,}")
col3.metric("Doanh thu", f"{doanhthu:,.0f} đ")
col4.metric("Lợi nhuận", f"{loinhuan:,.0f} đ")

st.info("Chọn menu bên trái để thao tác")