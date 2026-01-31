import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def connect_sheets():
    # Kiểm tra sự tồn tại của secrets trước khi truy cập
    if "gsheets" in st.secrets:
        print("Lay sheet connect info")
        creds_info = dict(st.secrets["gsheets"])
    else:
        # Nếu không tìm thấy, hiển thị hướng dẫn cụ thể trên giao diện app
        st.error("❌ Không tìm thấy thông tin cấu hình trong Streamlit Secrets!")
        st.info("Vui lòng vào Settings -> Secrets và thêm mục [gsheets] vào.")
        st.stop()

    try:
        # Xử lý ký tự xuống dòng cho private_key
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
            
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        gc = gspread.authorize(creds)
        
        # Thử mở file sheet
        return gc.open("QuanLyNhaThuoc")
    except Exception as e:
        st.error(f"❌ Lỗi xác thực hoặc mở file: {e}")
        st.stop()

def load_df(worksheet_name):
    try:
        sh = connect_sheets()
        worksheet = sh.worksheet(worksheet_name)
        return worksheet.get_all_records()
    except Exception as e:
        st.error(f"❌ Lỗi khi lấy dữ liệu từ tab '{worksheet_name}': {e}")
        return []
