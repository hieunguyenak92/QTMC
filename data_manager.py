import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- KET NOI GOOGLE SHEET ---
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if st.secrets.get("gcp_service_account"):
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name('google_key.json', scope)
        
        client = gspread.authorize(creds)
        sheet_url = st.secrets.get("sheet_url")
        if not sheet_url:
            return None
        return client.open_by_url(sheet_url)
    except Exception as e:
        st.error(f"Loi ket noi Database: {str(e)}")
        return None

# --- HAM HELPER: DOC DU LIEU AN TOAN ---
# Ham nay thay the cho get_all_records() de tranh loi "duplicate header"
def safe_get_data(worksheet):
    try:
        # Lay toan bo du lieu dang list of lists (raw)
        data = worksheet.get_all_values()
        if not data:
            return pd.DataFrame()
        
        # Dong dau tien la header
        headers = data[0]
        # Cac dong sau la du lieu
        rows = data[1:]
        
        # Xu ly truong hop Header bi rong hoac trung (Fix loi cua ban)
        seen = {}
        clean_headers = []
        for i, h in enumerate(headers):
            h = h.strip()
            if not h:
                h = f"Column_{i}" # Dat ten tam neu rong
            if h in seen:
                seen[h] += 1
                h = f"{h}_{seen[h]}" # Doi ten neu trung (VD: GiaBan_1)
            else:
                seen[h] = 0
            clean_headers.append(h)
            
        df = pd.DataFrame(rows, columns=clean_headers)
        return df
    except Exception as e:
        st.error(f"Lỗi đọc dữ liệu: {e}")
        return pd.DataFrame()

# --- 1. TAI TON KHO ---
def load_inventory():
    sh = get_connection()
    if sh:
        try:
            wks = sh.worksheet("TonKho")
            # SU DUNG HAM AN TOAN MOI
            df = safe_get_data(wks)
            
            # Chuan hoa so lieu
            numeric_cols = ['SoLuong', 'GiaNhap', 'GiaBan']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            return df
        except Exception as e:
            st.error(f"Khong tim thay sheet TonKho: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- 2. TAI LICH SU BAN ---
def load_sales_history():
    sh = get_connection()
    if sh:
        try:
            wks = sh.worksheet("LichSuBan")
            df = safe_get_data(wks)
            
            if not df.empty and 'NgayBan' in df.columns:
                df['NgayBan'] = pd.to_datetime(df['NgayBan'], errors='coerce')
                
            numeric_cols = ['SoLuong', 'GiaBan', 'ThanhTien', 'GiaVonLucBan', 'LoiNhuan']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

# --- 3. XU LY BAN HANG ---
def process_checkout(cart_items):
    sh = get_connection()
    if not sh: return False
    
    try:
        ws_inventory = sh.worksheet("TonKho")
        ws_sales = sh.worksheet("LichSuBan")
        
        # Doc du lieu bang ham an toan
        df_inv = safe_get_data(ws_inventory)
        
        sales_rows = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        order_id = datetime.now().strftime("%Y%m%d%H%M%S")
        
        for item in cart_items:
            ma_sp = item['MaSanPham']
            qty_sell = item['SoLuongBan']
            
            # Tim vi tri trong DataFrame
            match_idx = df_inv.index[df_inv['MaSanPham'] == ma_sp].tolist()
            
            if match_idx:
                idx = match_idx[0]
                # Lay gia tri hien tai
                current_qty = float(df_inv.at[idx, 'SoLuong'])
                cost_price = float(df_inv.at[idx, 'GiaNhap'])
                
                new_qty = current_qty - qty_sell
                
                # Update Google Sheet (Index + 2 vi header=1, index=0)
                ws_inventory.update_cell(idx + 2, 4, new_qty)
                
                revenue = item['GiaBan'] * qty_sell
                profit = (item['GiaBan'] - cost_price) * qty_sell
                
                sales_rows.append([
                    timestamp, order_id, ma_sp, item['TenSanPham'], 
                    item['DonVi'], qty_sell, item['GiaBan'], 
                    revenue, cost_price, profit
                ])
        
        if sales_rows:
            ws_sales.append_rows(sales_rows)
            return True
            
    except Exception as e:
        st.error(f"Lỗi hệ thống khi lưu đơn: {str(e)}")
        return False
    return False

# --- 4. XU LY NHAP HANG ---
def process_import(import_list):
    sh = get_connection()
    if not sh: return False
    
    try:
        ws_inventory = sh.worksheet("TonKho")
        ws_import = sh.worksheet("LichSuNhap")
        
        # Doc du lieu bang ham an toan (FIX LOI TAI DAY)
        df_inv = safe_get_data(ws_inventory)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        import_log_rows = []
        
        for item in import_list:
            ma_sp = item['MaSanPham']
            qty_in = item['SoLuong']
            price_in = item['GiaNhap']
            price_out = item['GiaBan']
            
            exists = False
            row_idx_update = -1
            
            # Check ton tai
            if not df_inv.empty and 'MaSanPham' in df_inv.columns:
                matches = df_inv.index[df_inv['MaSanPham'] == ma_sp].tolist()
                if matches:
                    exists = True
                    row_idx_update = matches[0]
            
            if exists:
                # Update
                current_qty = float(df_inv.at[row_idx_update, 'SoLuong'])
                new_qty = current_qty + qty_in
                
                # Update cell truc tiep
                ws_inventory.update_cell(row_idx_update + 2, 4, new_qty) # SoLuong
                ws_inventory.update_cell(row_idx_update + 2, 5, price_in) # GiaNhap
                ws_inventory.update_cell(row_idx_update + 2, 6, price_out) # GiaBan
            else:
                # Insert
                new_row = [
                    ma_sp, item['TenSanPham'], item['DonVi'], 
                    qty_in, price_in, price_out, item.get('NhaCungCap', '')
                ]
                ws_inventory.append_row(new_row)
            
            import_log_rows.append([
                timestamp, ma_sp, item['TenSanPham'], item.get('NhaCungCap', ''),
                item['DonVi'], qty_in, price_in, qty_in * price_in
            ])
            
        if import_log_rows:
            ws_import.append_rows(import_log_rows)
            
        return True
    except Exception as e:
        st.error(f"Lỗi nhập hàng: {str(e)}")
        return False