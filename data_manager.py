import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- KET NOI GOOGLE SHEET ---
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # Ưu tiên lấy từ secrets
        if st.secrets.get("gcp_service_account"):
            creds_dict = dict(st.secrets["gcp_service_account"]) # Chuyen ve dict chuan
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # Fallback file json local
            creds = ServiceAccountCredentials.from_json_keyfile_name('google_key.json', scope)
        
        client = gspread.authorize(creds)
        sheet_url = st.secrets.get("sheet_url")
        if not sheet_url:
            st.error("Chưa cấu hình 'sheet_url' trong secrets.")
            return None
        return client.open_by_url(sheet_url)
    except Exception as e:
        st.error(f"Lỗi kết nối Database: {str(e)}")
        return None

# --- HAM HELPER: DOC DU LIEU AN TOAN ---
def safe_get_data(worksheet):
    try:
        data = worksheet.get_all_values()
        if not data:
            return pd.DataFrame()
        
        headers = data[0]
        rows = data[1:]
        
        seen = {}
        clean_headers = []
        for i, h in enumerate(headers):
            h = str(h).strip()
            if not h: h = f"Column_{i}"
            if h in seen:
                seen[h] += 1
                h = f"{h}_{seen[h]}"
            else:
                seen[h] = 0
            clean_headers.append(h)
            
        df = pd.DataFrame(rows, columns=clean_headers)
        return df
    except Exception as e:
        st.error(f"Lỗi đọc dữ liệu sheet: {e}")
        return pd.DataFrame()

# --- 1. TAI TON KHO (CÓ CACHE) ---
# Dùng ttl=60s để không gọi Google Sheet quá nhiều, nhưng vẫn update kịp thời
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
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            return df
        except Exception as e:
            st.error(f"Lỗi tải tồn kho: {e}")
    return pd.DataFrame()

# --- 2. TAI LICH SU BAN (KHÔNG CACHE ĐỂ REALTIME) ---
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
            pass
    return pd.DataFrame()

# --- 3. XU LY BAN HANG ---
def process_checkout(cart_items):
    sh = get_connection()
    if not sh: return False
    
    try:
        ws_inventory = sh.worksheet("TonKho")
        ws_sales = sh.worksheet("LichSuBan")
        
        df_inv = safe_get_data(ws_inventory)
        
        sales_rows = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        order_id = datetime.now().strftime("%Y%m%d%H%M%S") # Mã đơn duy nhất theo giây
        
        for item in cart_items:
            ma_sp = item['MaSanPham']
            qty_sell = item['SoLuongBan']
            
            # Tìm vị trí sản phẩm trong kho
            match_idx = df_inv.index[df_inv['MaSanPham'] == ma_sp].tolist()
            
            if match_idx:
                idx = match_idx[0]
                current_qty = float(df_inv.at[idx, 'SoLuong'])
                cost_price = float(df_inv.at[idx, 'GiaNhap'])
                
                new_qty = current_qty - qty_sell
                
                # Cập nhật tồn kho (Row + 2 vì header và 0-index)
                ws_inventory.update_cell(idx + 2, 4, new_qty)
                
                revenue = item['GiaBan'] * qty_sell
                profit = (item['GiaBan'] - cost_price) * qty_sell
                
                # Cấu trúc lưu: NgayBan, MaDonHang, MaSP, TenSP, DonVi, SoLuong, GiaBan, ThanhTien, GiaVon, LoiNhuan
                sales_rows.append([
                    timestamp, order_id, ma_sp, item['TenSanPham'], 
                    item['DonVi'], qty_sell, item['GiaBan'], 
                    revenue, cost_price, profit
                ])
        
        if sales_rows:
            ws_sales.append_rows(sales_rows)
            st.cache_data.clear() # Xóa cache tồn kho để làm mới
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
                current_qty = float(df_inv.at[row_idx_update, 'SoLuong'])
                new_qty = current_qty + qty_in
                
                # Update Inventory
                ws_inventory.update_cell(row_idx_update + 2, 4, new_qty) 
                ws_inventory.update_cell(row_idx_update + 2, 5, price_in) 
                ws_inventory.update_cell(row_idx_update + 2, 6, price_out)
            else:
                # Insert New Product
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
            st.cache_data.clear()
            
        return True
    except Exception as e:
        st.error(f"Lỗi nhập hàng: {str(e)}")
        return False

# --- 5. XU LY HOAN TRA / XOA DON (NEW) ---
def process_return(order_id, product_id, qty_return, original_time):
    """
    Xóa giao dịch khỏi LichSuBan và cộng lại tồn kho vào TonKho.
    Xác định dòng cần xóa dựa trên MaDonHang, MaSP và ThoiGian
    """
    sh = get_connection()
    if not sh: return False

    try:
        ws_sales = sh.worksheet("LichSuBan")
        ws_inventory = sh.worksheet("TonKho")

        # 1. Tìm dòng trong LichSuBan để xóa
        # Lưu ý: Tìm chính xác để tránh xóa nhầm
        records = ws_sales.get_all_values()
        
        row_to_delete = -1
        
        # Duyệt từ dưới lên để tìm nhanh hơn (đơn mới thường ở cuối)
        for i in range(len(records) - 1, 0, -1):
            row = records[i]
            # row[0]: NgayBan, row[1]: MaDonHang, row[2]: MaSP
            # So sánh chuỗi thời gian, mã đơn và mã SP
            r_time = str(row[0])
            r_order = str(row[1])
            r_sp = str(row[2])
            
            # Chỉ so sánh chuỗi thời gian đến phút hoặc giây nếu cần
            # Ở đây ta so sánh chính xác chuỗi đã lưu
            if r_order == str(order_id) and r_sp == str(product_id):
                 row_to_delete = i + 1 # Google Sheet index start at 1
                 break
        
        if row_to_delete == -1:
            st.error("Không tìm thấy đơn hàng gốc để hoàn trả!")
            return False

        # 2. Cộng lại tồn kho
        df_inv = safe_get_data(ws_inventory)
        match_idx = df_inv.index[df_inv['MaSanPham'] == str(product_id)].tolist()
        
        if match_idx:
            idx = match_idx[0]
            current_qty = float(df_inv.at[idx, 'SoLuong'])
            new_qty = current_qty + float(qty_return)
            ws_inventory.update_cell(idx + 2, 4, new_qty)
        else:
            st.warning("Sản phẩm này không còn trong danh mục tồn kho, nhưng vẫn sẽ xóa lịch sử bán.")

        # 3. Xóa dòng lịch sử bán
        ws_sales.delete_rows(row_to_delete)
        
        st.cache_data.clear()
        return True

    except Exception as e:
        st.error(f"Lỗi xử lý hoàn trả: {e}")
        return False
