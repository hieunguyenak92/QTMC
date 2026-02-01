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
@st.cache_data(ttl=60)
def load_inventory():
    sh = get_connection()
    if sh:
        try:
            wks = sh.worksheet("TonKho")
            df = safe_get_data(wks)
            
            # Đảm bảo các cột quan trọng tồn tại
            expected_cols = ['MaSanPham', 'TenSanPham', 'SoLuong', 'GiaBan', 'GiaNhap', 'DonVi']
            for col in expected_cols:
                if col not in df.columns:
                    # Nếu thiếu cột, tạo cột rỗng để không lỗi app
                    df[col] = 0 if 'Gia' in col or 'SoLuong' in col else ""

            numeric_cols = ['SoLuong', 'GiaNhap', 'GiaBan']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            return df
        except Exception as e:
            st.error(f"Lỗi tải tồn kho: {e}")
    return pd.DataFrame()

# --- 2. TAI LICH SU BAN (FIX KEYERROR DỨT ĐIỂM) ---
def load_sales_history():
    sh = get_connection()
    if sh:
        try:
            wks = sh.worksheet("LichSuBan")
            # Lấy toàn bộ dữ liệu thô (list of lists)
            data = wks.get_all_values()
            
            # Nếu chỉ có header hoặc trống thì trả về rỗng
            if len(data) < 2: 
                return pd.DataFrame(columns=['NgayBan', 'MaDonHang', 'MaSanPham', 'TenSanPham', 'DonVi', 'SoLuong', 'GiaBan', 'ThanhTien'])

            # Bỏ dòng header của Google Sheet, chỉ lấy dữ liệu
            rows = data[1:]
            
            # Tạo DataFrame mới
            df = pd.DataFrame(rows)
            
            # ĐỊNH NGHĨA LẠI TÊN CỘT THEO ĐÚNG THỨ TỰ (Mapping)
            # Điều này đảm bảo dù trên Sheet bạn đặt tên là gì, Code vẫn hiểu đúng.
            # Cấu trúc lưu: [0:Ngay, 1:MaDon, 2:MaSP, 3:Ten, 4:DonVi, 5:SL, 6:Gia, 7:Tong, 8:Von, 9:Lai]
            
            # Chỉ lấy số lượng cột có dữ liệu thực tế để tránh lỗi lệch cột
            num_cols = df.shape[1]
            
            # Danh sách tên cột chuẩn mà Code main.py đang cần
            standard_headers = [
                'NgayBan', 'MaDonHang', 'MaSanPham', 'TenSanPham', 
                'DonVi', 'SoLuong', 'GiaBan', 'ThanhTien', 
                'GiaVonLucBan', 'LoiNhuan'
            ]
            
            # Gán tên cột cho DataFrame
            # Nếu file Excel có nhiều cột hơn chuẩn, giữ nguyên các cột thừa
            # Nếu ít hơn, chỉ gán cho số lượng cột hiện có
            current_headers = standard_headers[:num_cols] + [f"Col_{i}" for i in range(len(standard_headers), num_cols)]
            df.columns = current_headers

            # Xử lý dữ liệu
            if 'NgayBan' in df.columns:
                df['NgayBan'] = pd.to_datetime(df['NgayBan'], errors='coerce')
                
            numeric_cols = ['SoLuong', 'GiaBan', 'ThanhTien', 'GiaVonLucBan', 'LoiNhuan']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
            return df
        except Exception as e:
            st.warning(f"Chưa tải được lịch sử bán: {str(e)}")
            return pd.DataFrame()
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
        order_id = datetime.now().strftime("%Y%m%d%H%M%S")
        
        for item in cart_items:
            ma_sp = str(item['MaSanPham'])
            qty_sell = item['SoLuongBan']
            
            # Tìm vị trí sản phẩm
            match_idx = df_inv.index[df_inv['MaSanPham'] == ma_sp].tolist()
            
            if match_idx:
                idx = match_idx[0]
                current_qty = float(df_inv.at[idx, 'SoLuong'])
                cost_price = float(df_inv.at[idx, 'GiaNhap'])
                
                new_qty = current_qty - qty_sell
                
                # Update Inventory (Row + 2)
                ws_inventory.update_cell(idx + 2, 4, new_qty)
                
                revenue = item['GiaBan'] * qty_sell
                profit = (item['GiaBan'] - cost_price) * qty_sell
                
                # LƯU Ý THỨ TỰ CỘT NÀY PHẢI KHỚP VỚI HÀM LOAD Ở TRÊN
                sales_rows.append([
                    timestamp,      # 0: NgayBan
                    order_id,       # 1: MaDonHang
                    ma_sp,          # 2: MaSanPham
                    item['TenSanPham'], # 3: TenSanPham
                    item['DonVi'],  # 4: DonVi
                    qty_sell,       # 5: SoLuong
                    item['GiaBan'], # 6: GiaBan
                    revenue,        # 7: ThanhTien
                    cost_price,     # 8: GiaVon
                    profit          # 9: LoiNhuan
                ])
        
        if sales_rows:
            ws_sales.append_rows(sales_rows)
            st.cache_data.clear()
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
                
                ws_inventory.update_cell(row_idx_update + 2, 4, new_qty) 
                ws_inventory.update_cell(row_idx_update + 2, 5, price_in) 
                ws_inventory.update_cell(row_idx_update + 2, 6, price_out)
            else:
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

# --- 5. XU LY HOAN TRA / XOA DON ---
def process_return(order_id, product_id, qty_return, original_time):
    sh = get_connection()
    if not sh: return False

    try:
        ws_sales = sh.worksheet("LichSuBan")
        ws_inventory = sh.worksheet("TonKho")

        # Load toàn bộ data để tìm dòng xóa
        records = ws_sales.get_all_values()
        row_to_delete = -1
        
        # Duyệt ngược từ dưới lên (đơn mới nhất)
        for i in range(len(records) - 1, 0, -1):
            row = records[i]
            # row[1] là cột thứ 2 (MaDonHang)
            # row[2] là cột thứ 3 (MaSanPham)
            if len(row) > 2:
                r_order = str(row[1]).strip()
                r_sp = str(row[2]).strip()
                
                if r_order == str(order_id) and r_sp == str(product_id):
                     row_to_delete = i + 1
                     break
        
        if row_to_delete == -1:
            st.error("Không tìm thấy đơn hàng gốc để hoàn trả!")
            return False

        # Cộng lại kho
        df_inv = safe_get_data(ws_inventory)
        match_idx = df_inv.index[df_inv['MaSanPham'] == str(product_id)].tolist()
        
        if match_idx:
            idx = match_idx[0]
            current_qty = float(df_inv.at[idx, 'SoLuong'])
            new_qty = current_qty + float(qty_return)
            ws_inventory.update_cell(idx + 2, 4, new_qty)

        # Xóa dòng lịch sử
        ws_sales.delete_rows(row_to_delete)
        
        st.cache_data.clear()
        return True

    except Exception as e:
        st.error(f"Lỗi xử lý hoàn trả: {e}")
        return False
