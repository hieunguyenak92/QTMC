import streamlit as st
from utils.sheets import load_df
from utils.header import show_header

show_header()
st.title("📊 Tồn Kho")

df = load_df("SanPham").copy()
df["ThanhTienVon"] = df["TonKho"] * df["GiaNhap"]
df["ThanhTienBan"] = df["TonKho"] * df["GiaBan"]

sort_order = st.selectbox("Sắp xếp theo tồn kho", ["Tăng dần", "Giảm dần"])
if sort_order == "Tăng dần":
    df = df.sort_values("TonKho", ascending=True)
else:
    df = df.sort_values("TonKho", ascending=False)

st.dataframe(
    df[["TenThuoc", "TonKho", "DonVi", "GiaNhap", "GiaBan", "ThanhTienVon", "ThanhTienBan"]].style.format({
        "GiaNhap": "{:,.0f} đ",
        "GiaBan": "{:,.0f} đ",
        "ThanhTienVon": "{:,.0f} đ",
        "ThanhTienBan": "{:,.0f} đ"
    }),
    use_container_width=True
)