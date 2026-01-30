import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# Scopes cần thiết
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def connect_sheets():
    try:
        # --- PHẦN QUAN TRỌNG: ĐỒNG BỘ KEY ---
        # Code này sẽ tự động tìm xem bạn đặt tên secrets là [gsheets] hay [gcp_service_account]
        # Giúp tránh lỗi KeyError dù bạn cấu hình kiểu nào
        if "gsheets" in st.secrets:
            secrets_dict = dict(st.secrets["gsheets"])
        elif "gcp_service_account" in st.secrets:
            secrets_dict = dict(st.secrets["gcp_service_account"])
        else:
            st.error("🚨 Lỗi: Không tìm thấy mục [gsheets] hoặc [gcp_service_account] trong Secrets.")
            st.stop()
            
        # Xử lý lỗi ký tự xuống dòng trong private_key (Fix lỗi RefreshError)
        if "private_key" in secrets_dict:
            secrets_dict["private_key"] = secrets_dict["private_key"].replace("\\n", "\n")

        # Tạo credentials
        creds = Credentials.from_service_account_info(
            secrets_dict,
            scopes=SCOPES
        )

        gc = gspread.authorize(creds)
        
        # Mở Sheet (Đảm bảo tên sheet trên Google Drive là QuanLyNhaThuoc)
        return gc.open("QuanLyNhaThuoc")

    except Exception as e:
        st.error(f"🚨 Lỗi kết nối: {e}")
        st.stop()

def load_df(worksheet_name):
    try:
        sh = connect_sheets()
        worksheet = sh.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        return data
    except Exception as e:
        st.error(f"🚨 Lỗi đọc sheet '{worksheet_name}': {e}")
        st.stop()
