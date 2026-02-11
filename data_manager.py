import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import re  # Để clean symbol robust / extract sheet key
import time
import pytz  # Để set timezone VN

# NOTE: User request: do not use clean_to_float anymore.
# Keeping function for backward compatibility if referenced elsewhere,
# but it is no longer called anywhere in this file.
def clean_to_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0

def _extract_sheet_key(sheet_url):
    if not sheet_url:
        return None
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    return m.group(1) if m else None

def _parse_sheet_datetime_series(series):
    # Parse cả chuỗi ngày thường và serial date từ Google Sheets.
    parsed = pd.to_datetime(series, errors='coerce')
    numeric_vals = pd.to_numeric(series, errors='coerce')
    serial_mask = parsed.isna() & numeric_vals.notna()
    if serial_mask.any():
        parsed.loc[serial_mask] = pd.to_datetime(
            numeric_vals.loc[serial_mask],
            unit='D',
            origin='1899-12-30',
            errors='coerce'
        )
    return parsed

def _get_sheet_headers(worksheet):
    try:
        headers = worksheet.row_values(1)
    except Exception:
        headers = []
    return [str(h).strip() for h in headers]

def _ensure_sheet_column(worksheet, headers, column_name):
    if column_name not in headers:
        worksheet.update_cell(1, len(headers) + 1, column_name)
        headers.append(column_name)
    return headers

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

        # Retry + fallback to open_by_key to avoid Drive API 500 errors
        last_err = None
        sheet_key = _extract_sheet_key(sheet_url)
        for attempt in range(3):
            try:
                return client.open_by_url(sheet_url)
            except Exception as e:
                last_err = e
                if sheet_key:
                    try:
                        return client.open_by_key(sheet_key)
                    except Exception as e2:
                        last_err = e2
                time.sleep(0.7 * (attempt + 1))
        raise last_err
    except Exception as e:
        st.error(f"Lỗi kết nối Database: {str(e)}")
        return None

# --- HAM HELPER: DOC DU LIEU AN TOAN ---
def safe_get_data(worksheet):
    try:
        try:
            # Lấy giá trị thô (không theo định dạng hiển thị) để tránh lỗi dấu phân cách
            data = worksheet.get("A:Z", value_render_option='UNFORMATTED_VALUE')
        except Exception:
            try:
                data = worksheet.get_all_values(value_render_option='UNFORMATTED_VALUE')
            except Exception:
                # Fallback nếu version gspread cũ
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

# --- 1. TAI TON KHO (CLEAN PRICE KHI LOAD) ---
@st.cache_data(ttl=60)
def load_inventory():
    sh = get_connection()
    if sh:
        try:
            wks = sh.worksheet("TonKho")
            df = safe_get_data(wks)
            
            # Không dùng clean_to_float; dùng to_numeric tối thiểu để tránh lỗi tính toán
            numeric_cols = ['SoLuong', 'GiaNhap', 'GiaBan']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

# --- 2. TAI LICH SU BAN (CLEAN PRICE KHI LOAD) ---
def load_sales_history():
    sh = get_connection()
    if sh:
        try:
            wks = sh.worksheet("LichSuBan")
            try:
                data = wks.get("A:J", value_render_option='UNFORMATTED_VALUE')
            except Exception:
                try:
                    data = wks.get_all_values(value_render_option='UNFORMATTED_VALUE')
                except Exception:
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
                
            # Không dùng clean_to_float; dùng to_numeric tối thiểu để tránh lỗi tính toán
            numeric_cols = ['SoLuong', 'GiaBan', 'ThanhTien', 'GiaVonLucBan', 'LoiNhuan']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            return df
        except Exception as e:
            st.warning(f"Lỗi tải lịch sử: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- 2b. TAI DU LIEU CONG NO ---
@st.cache_data(ttl=60)
def load_debt_records():
    sh = get_connection()
    COL_NAMES = ['TenKH', 'Ngay', 'TenSanPham', 'SoLuong', 'ThanhTien']
    if sh:
        try:
            wks = sh.worksheet("CongNo")
            df = safe_get_data(wks)

            if df.empty:
                return pd.DataFrame(columns=COL_NAMES + ['MaPhieuNo', 'NgayRaw', 'NgayParsed'])

            df.columns = [str(c).strip() for c in df.columns]
            for col in COL_NAMES:
                if col not in df.columns:
                    df[col] = ''
            if 'MaPhieuNo' not in df.columns:
                df['MaPhieuNo'] = ''

            df = df[COL_NAMES + ['MaPhieuNo'] + [c for c in df.columns if c not in COL_NAMES + ['MaPhieuNo']]]
            df['TenKH'] = df['TenKH'].astype(str).str.strip()
            df['TenSanPham'] = df['TenSanPham'].astype(str).str.strip()
            df['NgayRaw'] = df['Ngay'].astype(str).str.strip()
            df['NgayParsed'] = _parse_sheet_datetime_series(df['Ngay'])
            df['SoLuong'] = pd.to_numeric(df['SoLuong'], errors='coerce').fillna(0)
            df['ThanhTien'] = pd.to_numeric(df['ThanhTien'], errors='coerce').fillna(0)
            df['MaPhieuNo'] = df['MaPhieuNo'].astype(str).str.strip()

            legacy_fallback = (
                "LEGACY|"
                + df['TenKH'].astype(str).str.strip()
                + "|"
                + df['NgayRaw'].astype(str).str.strip()
            )
            df.loc[df['MaPhieuNo'] == '', 'MaPhieuNo'] = legacy_fallback[df['MaPhieuNo'] == '']

            # Nếu sheet có cột trạng thái, chỉ lấy công nợ chưa thanh toán.
            if 'TrangThai' in df.columns:
                unpaid_mask = ~df['TrangThai'].astype(str).str.strip().str.lower().isin(['datra', 'da tra', 'paid'])
                df = df[unpaid_mask]

            df = df[(df['TenKH'] != '') & (df['TenSanPham'] != '')]
            return df.reset_index(drop=True)
        except Exception as e:
            st.warning(f"Lỗi tải công nợ: {e}")
            return pd.DataFrame(columns=COL_NAMES + ['MaPhieuNo', 'NgayRaw', 'NgayParsed'])
    return pd.DataFrame(columns=COL_NAMES + ['MaPhieuNo', 'NgayRaw', 'NgayParsed'])

# --- 3. XU LY BAN HANG (FIX: không clean giá từ cart vì đã là float) ---
def process_checkout(cart_items):
    sh = get_connection()
    if not sh: return False
    
    try:
        ws_inventory = sh.worksheet("TonKho")
        ws_sales = sh.worksheet("LichSuBan")
        
        # Dùng cùng nguồn với UI để đảm bảo số đã được parse ổn định
        df_inv = load_inventory()
        if df_inv.empty:
            st.error("Không tải được dữ liệu tồn kho.")
            return False
        if 'MaSanPham' in df_inv.columns:
            df_inv['MaSanPham'] = df_inv['MaSanPham'].astype(str).str.strip()
        
        # Không clean dữ liệu tồn kho theo yêu cầu
        
        sales_rows = []
        tz = pytz.timezone('Asia/Ho_Chi_Minh')  # VN time
        timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        order_id = datetime.now(tz).strftime("%Y%m%d%H%M%S")
        
        for item in cart_items:
            ma_sp = str(item['MaSanPham'])
            qty_sell = int(item['SoLuongBan'])  # SL luôn int
            
            match_idx = df_inv.index[df_inv['MaSanPham'] == ma_sp].tolist()
            
            if match_idx:
                idx = match_idx[0]
                try:
                    current_qty = float(df_inv.at[idx, 'SoLuong'])
                    # Giá bán lấy từ giỏ hàng (giá cuối cùng khách mua)
                    gia_ban = float(item['GiaBan'])
                    # Giá vốn lấy từ tồn kho để tính lợi nhuận
                    cost_price = float(df_inv.at[idx, 'GiaNhap'])
                except Exception:
                    st.error(f"Dữ liệu giá/SL của sản phẩm {ma_sp} không phải số. Vui lòng kiểm tra tồn kho.")
                    return False
                
                new_qty = current_qty - qty_sell
                ws_inventory.update_cell(idx + 2, 4, new_qty)
                
                # Lưu số nguyên VND để tránh lỗi định dạng khi ghi Sheets
                gia_ban_int = int(round(gia_ban))
                cost_price_int = int(round(cost_price))
                revenue = gia_ban_int * qty_sell
                profit = (gia_ban_int - cost_price_int) * qty_sell
                
                sales_rows.append([
                    timestamp,
                    order_id,
                    ma_sp,
                    item['TenSanPham'],
                    item['DonVi'],
                    qty_sell,
                    gia_ban_int,
                    revenue,
                    cost_price_int,
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

# --- 3b. XU LY BAN NO (CONG NO) ---
def process_debt_checkout(customer_name, cart_items):
    sh = get_connection()
    if not sh:
        return False

    customer_name = str(customer_name).strip()
    if not customer_name:
        st.error("Vui lòng nhập tên khách hàng.")
        return False
    if not cart_items:
        st.error("Giỏ công nợ đang trống.")
        return False

    try:
        ws_inventory = sh.worksheet("TonKho")
        ws_debt = sh.worksheet("CongNo")
        debt_headers = _get_sheet_headers(ws_debt)
        if not debt_headers:
            debt_headers = ['TenKH', 'Ngay', 'TenSanPham', 'SoLuong', 'ThanhTien']
            for col_idx, col_name in enumerate(debt_headers, start=1):
                ws_debt.update_cell(1, col_idx, col_name)

        for col_name in ['TenKH', 'Ngay', 'TenSanPham', 'SoLuong', 'ThanhTien', 'MaPhieuNo']:
            debt_headers = _ensure_sheet_column(ws_debt, debt_headers, col_name)

        header_idx = {name: idx for idx, name in enumerate(debt_headers)}

        df_inv = load_inventory()
        if df_inv.empty:
            st.error("Không tải được dữ liệu tồn kho.")
            return False
        if 'MaSanPham' not in df_inv.columns:
            st.error("Sheet tồn kho thiếu cột MaSanPham.")
            return False

        df_inv['MaSanPham'] = df_inv['MaSanPham'].astype(str).str.strip()

        # Validate toàn bộ trước để tránh ghi dở dang.
        inventory_updates = []
        debt_rows = []
        for item in cart_items:
            ma_sp = str(item.get('MaSanPham', '')).strip()
            ten_sp = str(item.get('TenSanPham', '')).strip()

            try:
                qty_sell = int(item.get('SoLuongBan', 0))
                sale_price_int = int(round(float(item.get('GiaBan', 0))))
            except Exception:
                st.error(f"Dữ liệu sản phẩm {ten_sp or ma_sp} không hợp lệ.")
                return False

            if qty_sell <= 0 or sale_price_int <= 0:
                st.error(f"Số lượng/giá bán của sản phẩm {ten_sp or ma_sp} không hợp lệ.")
                return False

            match_idx = df_inv.index[df_inv['MaSanPham'] == ma_sp].tolist()
            if not match_idx:
                st.error(f"Không tìm thấy sản phẩm mã {ma_sp} trong tồn kho.")
                return False

            idx = match_idx[0]
            current_qty = float(pd.to_numeric(df_inv.at[idx, 'SoLuong'], errors='coerce'))
            if pd.isna(current_qty):
                st.error(f"Dữ liệu số lượng tồn kho của {ten_sp or ma_sp} không hợp lệ.")
                return False
            if qty_sell > current_qty:
                st.error(f"Sản phẩm {ten_sp or ma_sp} không đủ tồn kho.")
                return False

            new_qty = current_qty - qty_sell
            df_inv.at[idx, 'SoLuong'] = new_qty
            inventory_updates.append((idx + 2, new_qty))
            debt_rows.append([ten_sp, qty_sell, sale_price_int * qty_sell])

        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        debt_id = datetime.now(tz).strftime("CN%Y%m%d%H%M%S%f")[:-3]

        for row_idx, new_qty in inventory_updates:
            ws_inventory.update_cell(row_idx, 4, new_qty)

        rows_to_append = []
        for ten_sp, qty_sell, thanh_tien in debt_rows:
            debt_row = [''] * len(debt_headers)
            debt_row[header_idx['TenKH']] = customer_name
            debt_row[header_idx['Ngay']] = timestamp
            debt_row[header_idx['TenSanPham']] = ten_sp
            debt_row[header_idx['SoLuong']] = qty_sell
            debt_row[header_idx['ThanhTien']] = thanh_tien
            debt_row[header_idx['MaPhieuNo']] = debt_id
            if 'TrangThai' in header_idx:
                debt_row[header_idx['TrangThai']] = 'ChuaTra'
            rows_to_append.append(debt_row)

        ws_debt.append_rows(rows_to_append)

        st.cache_data.clear()
        return debt_id
    except Exception as e:
        st.error(f"Lỗi tạo công nợ: {e}")
        return False

# --- 4. XU LY NHAP HANG (FIX: không clean giá từ list vì đã là float) ---
def process_import(import_list):
    sh = get_connection()
    if not sh: return False
    
    try:
        ws_inventory = sh.worksheet("TonKho")
        ws_import = sh.worksheet("LichSuNhap")
        df_inv = safe_get_data(ws_inventory)
        
        tz = pytz.timezone('Asia/Ho_Chi_Minh')  # VN time
        timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        import_log_rows = []
        
        for item in import_list:
            ma_sp = str(item['MaSanPham'])
            qty_in = item['SoLuong']
            price_in = int(round(float(item['GiaNhap'])))  # Đã là float từ input
            price_out = int(round(float(item['GiaBan'])))  # Đã là float từ input
            
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

# --- 4b. CAP NHAT GIA VON / GIA BAN ---
def update_product_prices(product_id, cost_price, sale_price=None):
    sh = get_connection()
    if not sh:
        return False

    try:
        ws_inventory = sh.worksheet("TonKho")
        df_inv = safe_get_data(ws_inventory)
        if df_inv.empty or 'MaSanPham' not in df_inv.columns:
            return False

        df_inv['MaSanPham'] = df_inv['MaSanPham'].astype(str).str.strip()
        pid = str(product_id).strip()

        match_idx = df_inv.index[df_inv['MaSanPham'] == pid].tolist()
        if not match_idx:
            return False

        idx = match_idx[0]
        cost_int = int(round(float(cost_price)))
        if cost_int <= 0:
            st.error("Giá vốn không hợp lệ.")
            return False

        ws_inventory.update_cell(idx + 2, 5, cost_int)

        if sale_price is not None:
            sale_int = int(round(float(sale_price)))
            if sale_int <= 0:
                st.error("Giá bán không hợp lệ.")
                return False
            ws_inventory.update_cell(idx + 2, 6, sale_int)

        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Lỗi cập nhật giá: {e}")
        return False

# --- 5. XU LY HOAN TRA (GIỮ NGUYÊN: XÓA DÒNG → KHÔNG CÒN _RET) ---
def process_return(order_id, product_id, qty_return):
    sh = get_connection()
    if not sh: return False

    try:
        ws_sales = sh.worksheet("LichSuBan")
        ws_inventory = sh.worksheet("TonKho")

        records = ws_sales.get_all_values()
        row_to_delete = None
        for i in range(1, len(records)):
            row = records[i]
            if len(row) >= 10 and str(row[1]).strip() == str(order_id) and str(row[2]).strip() == str(product_id):
                row_to_delete = i + 1  # Row index in sheet (1-based)
                break

        if not row_to_delete:
            return False

        # Xóa dòng trong sheet LichSuBan
        ws_sales.delete_rows(row_to_delete)

        # Cập nhật tồn kho
        df_inv = safe_get_data(ws_inventory)
        match_idx = df_inv.index[df_inv['MaSanPham'] == str(product_id)].tolist()
        if match_idx:
            idx = match_idx[0]
            current_qty = float(df_inv.at[idx, 'SoLuong'])
            ws_inventory.update_cell(idx + 2, 4, current_qty + qty_return)

        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Lỗi hoàn trả: {e}")
        return False

# --- 6. XU LY THANH TOAN CONG NO ---
def settle_debt(debt_id, customer_name=None, debt_time_raw=None):
    sh = get_connection()
    if not sh:
        return False

    debt_id = str(debt_id).strip()
    customer_name = str(customer_name).strip()
    debt_time_raw = str(debt_time_raw).strip()
    if not debt_id and (not customer_name or not debt_time_raw):
        return False

    try:
        ws_debt = sh.worksheet("CongNo")
        try:
            records = ws_debt.get("A:Z", value_render_option='UNFORMATTED_VALUE')
        except Exception:
            try:
                records = ws_debt.get_all_values(value_render_option='UNFORMATTED_VALUE')
            except Exception:
                records = ws_debt.get_all_values()
        if len(records) < 2:
            return False

        headers = [str(h).strip() for h in records[0]]
        idx_customer = headers.index('TenKH') if 'TenKH' in headers else 0
        idx_time = headers.index('Ngay') if 'Ngay' in headers else 1
        idx_debt = headers.index('MaPhieuNo') if 'MaPhieuNo' in headers else -1
        idx_status = headers.index('TrangThai') if 'TrangThai' in headers else -1

        matched_rows = []
        for i in range(1, len(records)):
            row = records[i]
            record_debt_id = str(row[idx_debt]).strip() if idx_debt >= 0 and idx_debt < len(row) else ''
            ten_kh = str(row[idx_customer]).strip() if idx_customer < len(row) else ''
            record_time = str(row[idx_time]).strip() if idx_time < len(row) else ''

            is_match = False
            if debt_id and record_debt_id:
                is_match = (record_debt_id == debt_id)
            elif customer_name and debt_time_raw:
                is_match = (ten_kh == customer_name and record_time == debt_time_raw)

            if is_match:
                matched_rows.append(i + 1)  # Sheet row index

        if not matched_rows:
            return False

        if idx_status >= 0:
            for sheet_row in matched_rows:
                ws_debt.update_cell(sheet_row, idx_status + 1, 'DaTra')
        else:
            # Xóa từ dưới lên để không lệch index.
            for sheet_row in sorted(matched_rows, reverse=True):
                ws_debt.delete_rows(sheet_row)

        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Lỗi cập nhật công nợ: {e}")
        return False
