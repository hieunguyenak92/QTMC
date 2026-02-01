import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# CLEAN PRICE DỨT ĐIỂM CHO GIÁ TIỀN NGUYÊN (INTEGER) - LOẠI BỎ MỌI DẤU PHẨY, CHẤM, KHOẢNG TRẮNG
def clean_to_float(s):
    if pd.isna(s):
        return 0.0
    # Chuyển thành string, loại bỏ mọi ký tự không phải số
    digits = ''.join(filter(str.isdigit, str(s)))
    # Nếu không có số nào thì trả về 0
    if not digits:
        return 0.0
    return float(digits)

# --- KET NOI GOOGLE SHEET ---
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if st.secrets.get("gcp_service_account"):
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name('google_key.json', scope)
        
        client = gspread.authorize(creds)
        sheet_url = st.secrets.get("sheet_url")
        if not sheet_url:
            return None
        return client.open_by_url(sheet_url)
    except Exception as e:
        st.error(f"Lỗi kết nối Database: {str(e)}")
        return None

# --- HAM HELPER: DOC DU LIEU AN TOAN ---
def safe_get_data(worksheet):
    try:
        data = worksheet.get_all_values()
        if not data: return pd.DataFrame()
        
        headers = data[0]
        rows = data[1:]
        
        df = pd.DataFrame(rows)
        
        seen = {}
        clean_headers = []
        for i, h in enumerate(headers):
            h = str(h).strip()
            if not h: h = f"Col_{i}"
            if h in seen:
                seen[h] += 1
                h = f"{h}_{seen[h]}"
            else:
                seen[h] = 0
            clean_headers.append(h)
            
        if len(df.columns) == len(clean_headers):
            df.columns = clean_headers
        else:
            df = df.iloc[:, :len(clean_headers)]
            df.columns = clean_headers[:df.shape[1]]
            
        return df
    except Exception as e:
        st.error(f"Lỗi đọc dữ liệu: {e}")
        return pd.DataFrame()

# --- 1. TAI TON KHO (CLEAN PRICE TRIỆT ĐỂ) ---
@st.cache_data(ttl=60)
def load_inventory():
    sh = get_connection()
    if sh:
        try:
            wks = sh.worksheet("TonKho")
            df = safe_get_data(wks)
            
            numeric_cols = ['SoLuong', 'GiaNhap', 'GiaBan']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].apply(clean_to_float)
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

# --- 2. TAI LICH SU BAN (CLEAN PRICE TRIỆT ĐỂ) ---
def load_sales_history():
    sh = get_connection()
    if sh:
        try:
            wks = sh.worksheet("LichSuBan")
            data = wks.get_all_values()
            
            COL_NAMES = [
                'NgayBan', 'MaDonHang', 'MaSanPham', 'TenSanPham', 
                'DonVi', 'SoLuong', 'GiaBan', 'ThanhTien', 
                'GiaVonLucBan', 'LoiNhuan'
            ]
            
            if len(data) < 2:
                return pd.DataFrame(columns=COL_NAMES)

            rows = data[1:]
            
            normalized_rows = []
            for row in rows:
                if len(row) < len(COL_NAMES):
                    row += [''] * (len(COL_NAMES) - len(row))
                elif len(row) > len(COL_NAMES):
                    row = row[:len(COL_NAMES)]
                normalized_rows.append(row)
            
            df = pd.DataFrame(normalized_rows, columns=COL_NAMES)

            if 'NgayBan' in df.columns:
                df['NgayBan'] = pd.to_datetime(df['NgayBan'], errors='coerce')
                
            numeric_cols = ['SoLuong', 'GiaBan', 'ThanhTien', 'GiaVonLucBan', 'LoiNhuan']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].apply(clean_to_float)
            
            return df
        except Exception as e:
            st.warning(f"Lỗi tải lịch sử: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- 3. XU LY BAN HANG (CLEAN PRICE KHI CHECKOUT) ---
def process_checkout(cart_items):
    sh = get_connection()
    if not sh: return False
    
    try:
        ws_inventory = sh.worksheet("TonKho")
        ws_sales = sh.worksheet("LichSuBan")
        
        df_inv = safe_get_data(ws_inventory)
        
        # Clean giá nhập trong kho (an toàn)
        if 'GiaNhap' in df_inv.columns:
            df_inv['GiaNhap'] = df_inv['GiaNhap'].apply(clean_to_float)
        
        sales_rows = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        order_id = datetime.now().strftime("%Y%m%d%H%M%S")
        
        for item in cart_items:
            ma_sp = str(item['MaSanPham'])
            qty_sell = int(item['SoLuongBan'])
            
            # Clean giá bán từ giỏ (hỗ trợ nếu là string)
            gia_ban = clean_to_float(item['GiaBan'])
            
            match_idx = df_inv.index[df_inv['MaSanPham'] == ma_sp].tolist()
            
            if match_idx:
                idx = match_idx[0]
                current_qty = clean_to_float(df_inv.at[idx, 'SoLuong'])
                cost_price = clean_to_float(df_inv.at[idx, 'GiaNhap'])
                
                new_qty = current_qty - qty_sell
                ws_inventory.update_cell(idx + 2, 4, new_qty)
                
                revenue = gia_ban * qty_sell
                profit = (gia_ban - cost_price) * qty_sell
                
                sales_rows.append([
                    timestamp,
                    order_id,
                    ma_sp,
                    item['TenSanPham'],
                    item['DonVi'],
                    qty_sell,
                    gia_ban,
                    revenue,
                    cost_price,
                    profit
                ])
        
        if sales_rows:
            ws_sales.append_rows(sales_rows)
            st.cache_data.clear()
            return True
            
    except Exception as e:
        st.error(f"Lỗi: {str(e)}")
        return False
    return False

# --- 4. XU LY NHAP HANG ---
def process_import(import_list):
    sh = get_connection()
    if not sh: return False
    
    try:
        ws_inventory = sh.worksheet("TonKho")
        ws_import = sh.worksheet("LichSuNhap")
        df_inv = safe_get_data(ws_inventory)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        import_log_rows = []
        
        for item in import_list:
            ma_sp = str(item['MaSanPham'])
            qty_in = item['SoLuong']
            price_in = item['GiaNhap']
            price_out = item['GiaBan']
            
            exists = False
            row_idx_update = -1
            
            if not df_inv.empty and 'MaSanPham' in df_inv.columns:
                matches = df_inv.index[df_inv['MaSanPham'] == ma_sp].tolist()
                if matches:
                    exists = True
                    row_idx_update = matches[0]
            
            if exists:
                current_qty = clean_to_float(df_inv.at[row_idx_update, 'SoLuong'])
                new_qty = current_qty + qty_in
                ws_inventory.update_cell(row_idx_update + 2, 4, new_qty) 
                ws_inventory.update_cell(row_idx_update + 2, 5, price_in) 
                ws_inventory.update_cell(row_idx_update + 2, 6, price_out)
            else:
                new_row = [ma_sp, item['TenSanPham'], item['DonVi'], qty_in, price_in, price_out, item.get('NhaCungCap', '')]
                ws_inventory.append_row(new_row)
            
            import_log_rows.append([timestamp, ma_sp, item['TenSanPham'], item.get('NhaCungCap', ''), item['DonVi'], qty_in, price_in, qty_in * price_in])
            
        if import_log_rows:
            ws_import.append_rows(import_log_rows)
            st.cache_data.clear()
            
        return True
    except Exception as e:
        st.error(f"Lỗi nhập hàng: {str(e)}")
        return False

# --- 5. XU LY HOAN TRA (CHUẨN: THÊM DÒNG ÂM) ---
def process_return(order_id, product_id, qty_return):
    sh = get_connection()
    if not sh: return False

    try:
        ws_sales = sh.worksheet("LichSuBan")
        ws_inventory = sh.worksheet("TonKho")

        records = ws_sales.get_all_values()
        original_row = None
        for i in range(1, len(records)):
            row = records[i]
            if len(row) >= 10 and str(row[1]).strip() == str(order_id) and str(row[2]).strip() == str(product_id):
                original_row = row
                break

        if not original_row:
            return False

        gia_ban = clean_to_float(original_row[6] or 0)
        gia_von = clean_to_float(original_row[8] or 0)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return_order_id = order_id + "_RET"

        ws_sales.append_row([
            timestamp,
            return_order_id,
            product_id,
            original_row[3],
            original_row[4],
            -qty_return,
            gia_ban,
            -gia_ban * qty_return,
            gia_von,
            -(gia_ban - gia_von) * qty_return
        ])

        df_inv = safe_get_data(ws_inventory)
        match_idx = df_inv.index[df_inv['MaSanPham'] == str(product_id)].tolist()
        if match_idx:
            idx = match_idx[0]
            current_qty = clean_to_float(df_inv.at[idx, 'SoLuong'])
            ws_inventory.update_cell(idx + 2, 4, current_qty + qty_return)

        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Lỗi hoàn trả: {e}")
        return False
