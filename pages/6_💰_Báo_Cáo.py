import streamlit as st
import plotly.express as px
import pandas as pd
from utils.sheets import load_df
from utils.header import show_header

show_header()
st.title("💰 Báo Cáo Lãi Lỗ")

df_nhap = load_df("NhapHang")
df_ban = load_df("BanHang")

if df_nhap.empty and df_ban.empty:
    st.info("Chưa có dữ liệu giao dịch")
else:
    df_ban["Ngay"] = pd.to_datetime(df_ban["Ngay"])
    df_nhap["Ngay"] = pd.to_datetime(df_nhap["Ngay"])
    
    tab1, tab2 = st.tabs(["Theo tháng", "Theo năm"])
    
    with tab1:
        df_month_ban = df_ban.groupby(df_ban["Ngay"].dt.to_period("M"))["TongTienBan"].sum().reset_index()
        df_month_nhap = df_nhap.groupby(df_nhap["Ngay"].dt.to_period("M"))["TongTienNhap"].sum().reset_index()
        df_month = pd.merge(df_month_ban, df_month_nhap, on="Ngay", how="outer").fillna(0)
        df_month["LoiNhuan"] = df_month["TongTienBan"] - df_month["TongTienNhap"]
        df_month["Ngay"] = df_month["Ngay"].astype(str)
        
        fig = px.bar(df_month, x="Ngay", y="TongTienBan", title="Doanh thu theo tháng")
        fig.add_scatter(x=df_month["Ngay"], y=df_month["LoiNhuan"], mode="lines+markers", name="Lợi nhuận")
        st.plotly_chart(fig, use_container_width=True)
        
    with tab2:
        df_year_ban = df_ban.groupby(df_ban["Ngay"].dt.to_period("Y"))["TongTienBan"].sum().reset_index()
        df_year_nhap = df_nhap.groupby(df_nhap["Ngay"].dt.to_period("Y"))["TongTienNhap"].sum().reset_index()
        df_year = pd.merge(df_year_ban, df_year_nhap, on="Ngay", how="outer").fillna(0)
        df_year["LoiNhuan"] = df_year["TongTienBan"] - df_year["TongTienNhap"]
        df_year["Ngay"] = df_year["Ngay"].astype(str)
        
        fig = px.bar(df_year, x="Ngay", y="TongTienBan", title="Doanh thu theo năm")
        fig.add_scatter(x=df_year["Ngay"], y=df_year["LoiNhuan"], mode="lines+markers", name="Lợi nhuận")
        st.plotly_chart(fig, use_container_width=True)