import gspread
import pandas as pd
import streamlit as st
from datetime import datetime

@st.cache_resource(ttl=60)
def connect_sheets():
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open("QuanLyNhaThuoc")  # Tên sheet chính xác của bạn
    return sh

def load_df(worksheet_name):
    sh = connect_sheets()
    ws = sh.worksheet(worksheet_name)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    # Filter theo cửa hàng hiện tại cho NhapHang và BanHang
    if worksheet_name in ["NhapHang", "BanHang"] and "CuaHang" in df.columns:
        df = df[df["CuaHang"] == st.session_state.get("cuahang", "MinhChau")].copy()
    return df

def append_row(worksheet_name, row):
    # Tự động thêm tên cửa hàng nếu là NhapHang hoặc BanHang
    if worksheet_name in ["NhapHang", "BanHang"]:
        row.append(st.session_state.get("cuahang", "MinhChau"))
    sh = connect_sheets()
    ws = sh.worksheet(worksheet_name)
    ws.append_row(row)

def update_stock(id_sp, delta_sl):
    df = load_df("SanPham")
    row_index = df[df["ID"] == id_sp].index[0] + 2  # +2 vì header + gspread bắt đầu từ 1
    current = df.loc[df["ID"] == id_sp, "TonKho"].values[0]
    new = current + delta_sl
    sh = connect_sheets()
    ws = sh.worksheet("SanPham")
    ws.update_cell(row_index, 6, new)  # Cột TonKho là cột 6 (A=1, B=2, ..., F=6)