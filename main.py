import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
import data_manager as dm

# --- 1. CAU HINH GIAO DIEN (VẤN ĐỀ 1) ---
st.set_page_config(
    page_title="Minh Châu 24h", 
    layout="wide", 
    page_icon="assets/logo.png" # Icon trên tab trình duyệt
)

# Custom CSS
st.markdown("""
<style>
    .stButton>button {width: 100%; border-radius: 8px; height: 3em; font-weight: bold;}
    div[data-testid="stMetricValue"] {font-size: 1.4rem; color: #0068C9;}
    .block-container {padding-top: 2rem;}
    
    /* Style cho Header */
    .header-title {
        font-size: 2.5em;
        font-weight: 700;
        color: #2E86C1;
        margin-bottom: 0px;
    }
    .header-subtitle {
        font-size: 1.2em;
        color: #555;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

# --- QUAN LY TRANG THAI (STATE) ---
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False
if 'sales_cart' not in st.session_state:
    st.session_state['sales_cart'] = []
if 'import_cart' not in st.session_state:
    st.session_state['import_cart'] = []

# --- HAM HO TRO ---
def format_currency(amount):
    return f"{amount:,.0f} đ"

# --- RENDER HEADER CHUNG (VẤN ĐỀ 1) ---
def render_header():
    # Chia cot de hien thi Logo va Ten
    c1, c2 = st.columns([1, 8])
    with c1:
        try:
            # Kiem tra file ton tai
            if os.path.exists("assets/logo.png"):
                st.image("assets/logo.png", width=90)
            else:
                st.write("💊") # Fallback icon
        except:
            st.write("💊")
            
    with c2:
        st.markdown('<p class="header-title">Quầy Thuốc Minh Châu 24h/7</p>', unsafe_allow_html=True)
        st.markdown('<p class="header-subtitle">Hệ thống quản lý dược phẩm thông minh</p>', unsafe_allow_html=True)
    st.divider()

# --- 1. MAN HINH DANG NHAP ---
def render_login():
    render_header()
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        with st.form("login_form"):
            st.subheader("🔒 Đăng Nhập Hệ Thống")
            password = st.text_input("Mật khẩu truy cập", type="password")
            submitted = st.form_submit_button("Truy cập ngay")
            
            if submitted:
                sys_pass = st.secrets.get("app_password", "123456")
                if password == sys_pass:
                    st.session_state['is_logged_in'] = True
                    st.rerun()
                else:
                    st.error("Sai mật khẩu! Vui lòng thử lại.")

# --- 2. MAN HINH BAN HANG (POS) ---
def render_sales(df_inv):
    st.subheader("💊 Bán Hàng Tại Quầy")
    
    col_search, col_cart = st.columns([5, 5], gap="large")
    
    # --- PHAN TIM KIEM SP ---
    with col_search:
        st.info("Tìm kiếm & Chọn hàng")
        if not df_inv.empty:
            df_inv['display_text'] = df_inv.apply(
                lambda x: f"{x['TenSanPham']} | Mã: {x['MaSanPham']} | Tồn: {x['SoLuong']} {x['DonVi']}", 
                axis=1
            )
            
            options = [""] + df_inv['display_text'].tolist()
            selected_str = st.selectbox("🔍 Nhập tên hoặc mã sản phẩm:", options=options, key="search_box")
            
            if selected_str:
                selected_item = df_inv[df_inv['display_text'] == selected_str].iloc[0]
                
                with st.container(border=True):
                    st.markdown(f"### {selected_item['TenSanPham']}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Mã SP", selected_item['MaSanPham'])
                    c2.metric("Đơn vị", selected_item['DonVi'])
                    c3.metric("Tồn kho", selected_item['SoLuong'])
                    
                    st.divider()
                    
                    c_price, c_qty = st.columns([1, 1])
                    c_price.metric("Giá bán", format_currency(selected_item['GiaBan']))
                    qty_sell = c_qty.number_input("Số lượng khách mua:", min_value=1, value=1, step=1)
                    
                    temp_total = qty_sell * selected_item['GiaBan']
                    st.success(f"Thành tiền: {format_currency(temp_total)}")
                    
                    if st.button("➕ Thêm vào giỏ hàng", type="primary"):
                        if qty_sell > selected_item['SoLuong']:
                            st.error(f"⚠️ Không đủ hàng! Chỉ còn {selected_item['SoLuong']} sản phẩm.")
                        else:
                            item = {
                                "MaSanPham": selected_item['MaSanPham'],
                                "TenSanPham": selected_item['TenSanPham'],
                                "DonVi": selected_item['DonVi'],
                                "GiaBan": float(selected_item['GiaBan']),
                                "SoLuongBan": qty_sell,
                                "ThanhTien": temp_total
                            }
                            st.session_state['sales_cart'].append(item)
                            st.toast(f"Đã thêm {selected_item['TenSanPham']}!", icon="✅")
                            
        else:
            st.warning("Kho hàng đang trống.")

    # --- PHAN GIO HANG ---
    with col_cart:
        st.info("Giỏ hàng hiện tại")
        cart = st.session_state['sales_cart']
        
        if cart:
            total_bill = 0
            df_cart = pd.DataFrame(cart)
            
            # Hien thi gon gang
            st.dataframe(
                df_cart[['TenSanPham', 'SoLuongBan', 'ThanhTien']], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "TenSanPham": "Tên SP",
                    "SoLuongBan": "SL",
                    "ThanhTien": st.column_config.NumberColumn("Thành tiền", format="%d đ")
                }
            )

            # Xoa gio hang
            col_del, col_space = st.columns([1, 3])
            if col_del.button("🗑 Xóa giỏ", type="secondary"):
                st.session_state['sales_cart'] = []
                st.rerun()

            for item in cart:
                total_bill += item['ThanhTien']
            
            st.divider()
            st.markdown(f"<h3 style='text-align: right; color: #D32F2F'>Tổng cộng: {format_currency(total_bill)}</h3>", unsafe_allow_html=True)
            
            if st.button("THANH TOÁN & IN HÓA ĐƠN", type="primary", use_container_width=True):
                with st.spinner("Đang xử lý giao dịch..."):
                    success = dm.process_checkout(cart)
                    if success:
                        st.session_state['sales_cart'] = []
                        st.balloons()
                        st.success("✅ Giao dịch thành công!")
                        st.rerun()
                    else:
                        st.error("Lỗi kết nối. Vui lòng thử lại.")
        else:
            st.caption("Chưa có sản phẩm nào.")

    st.divider()
    
    # --- VẤN ĐỀ 3: DANH SÁCH BÁN TRONG NGÀY & HOÀN TRẢ ---
    render_daily_sales_table()

def render_daily_sales_table():
    st.subheader("📋 Danh Sách Bán Trong Ngày")
    
    # Load lich su ban
    df_sales = dm.load_sales_history()
    
    if not df_sales.empty:
        # Filter theo ngay hien tai
        today_str = datetime.now().strftime('%Y-%m-%d')
        # Chuyen cot NgayBan ve string dang YYYY-MM-DD de so sanh
        df_sales['DateOnly'] = df_sales['NgayBan'].dt.strftime('%Y-%m-%d')
        df_today = df_sales[df_sales['DateOnly'] == today_str].copy()
        
        if not df_today.empty:
            # Hien thi bang
            # Sap xep moi nhat len dau
            df_today = df_today.sort_values(by='NgayBan', ascending=False)
            
            # Tạo layout từng dòng để có nút bấm
            # Header
            cols = st.columns([1, 3, 1, 1, 2, 2, 1.5])
            headers = ["Giờ", "Tên SP", "Đơn Vị", "SL", "Giá", "Tổng", "Thao tác"]
            for col, h in zip(cols, headers):
                col.markdown(f"**{h}**")
            
            st.markdown("---")
            
            for index, row in df_today.iterrows():
                c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 3, 1, 1, 2, 2, 1.5])
                
                time_str = row['NgayBan'].strftime('%H:%M')
                
                c1.write(time_str)
                c2.write(f"{row['TenSanPham']}")
                c3.write(row['DonVi'])
                c4.write(f"**{row['SoLuong']}**")
                c5.write(f"{row['GiaBan']:,.0f}")
                c6.write(f":blue[{row['ThanhTien']:,.0f}]")
                
                # Nut Hoan Tra
                # Dung key duy nhat dua tren MaDonHang va MaSP
                btn_key = f"btn_return_{row['MaDonHang']}_{row['MaSanPham']}"
                
                if c7.button("Hoàn trả", key=btn_key, type="primary"):
                    with st.spinner("Đang hoàn trả kho..."):
                         # Goi ham process_return trong data_manager
                         success = dm.process_return(
                             order_id=row['MaDonHang'], 
                             product_id=row['MaSanPham'], 
                             qty_return=row['SoLuong'],
                             original_time=row['NgayBan']
                         )
                         if success:
                             st.toast("Đã hoàn trả và cập nhật kho!", icon="✅")
                             st.rerun()
                         else:
                             st.error("Lỗi hoàn trả.")
            
        else:
            st.info("Hôm nay chưa có đơn hàng nào.")
    else:
        st.info("Chưa có dữ liệu lịch sử.")

# --- 3. MAN HINH NHAP HANG (IMPORT) ---
def render_import(df_inv):
    st.subheader("📦 Nhập Kho Hàng Hóa")
    
    tab1, tab2 = st.tabs(["NHẬP HÀNG CÓ SẴN", "THÊM SẢN PHẨM MỚI"])
    
    # --- Tab 1: Hang co san ---
    with tab1:
        if not df_inv.empty:
            df_inv['imp_display'] = df_inv.apply(lambda x: f"{x['TenSanPham']} - {x['MaSanPham']}", axis=1)
            options_imp = [""] + df_inv['imp_display'].tolist()
            
            sel_item = st.selectbox("Chọn sản phẩm nhập thêm:", options=options_imp)
            
            if sel_item:
                curr_item = df_inv[df_inv['imp_display'] == sel_item].iloc[0]
                
                st.write(f"Tồn hiện tại: **{curr_item['SoLuong']} {curr_item['DonVi']}**")
                
                with st.form("form_add_stock"):
                    c1, c2, c3 = st.columns(3)
                    qty_in = c1.number_input("Số lượng nhập thêm", min_value=1, value=10)
                    price_in = c2.number_input("Giá nhập mới", min_value=0.0, value=float(curr_item['GiaNhap']))
                    price_out = c3.number_input("Giá bán mới (nếu đổi)", min_value=0.0, value=float(curr_item['GiaBan']))
                    
                    if st.form_submit_button("Thêm vào phiếu nhập"):
                        row = {
                            "MaSanPham": curr_item['MaSanPham'],
                            "TenSanPham": curr_item['TenSanPham'],
                            "DonVi": curr_item['DonVi'],
                            "NhaCungCap": curr_item.get('NhaCungCap', ''),
                            "SoLuong": qty_in,
                            "GiaNhap": price_in,
                            "GiaBan": price_out,
                            "ThanhTien": qty_in * price_in
                        }
                        st.session_state['import_cart'].append(row)
                        st.success("Đã thêm!")
                        st.rerun()
        else:
            st.warning("Kho trống.")

    # --- Tab 2: Them moi (VẤN ĐỀ 2) ---
    with tab2:
        st.info("Khai báo sản phẩm lần đầu tiên nhập về nhà thuốc.")
        
        # LOGIC AUTO ID (VẤN ĐỀ 2)
        # Dem so luong san pham hien co + 1
        next_id = len(df_inv) + 1 if not df_inv.empty else 1
        
        with st.form("form_new_product"):
            c1, c2 = st.columns([1, 3])
            # Pre-fill Ma San Pham
            new_ma = c1.text_input("Mã Sản Phẩm (Tự động)", value=str(next_id)) 
            new_ten = c2.text_input("Tên Sản Phẩm (*Bắt buộc)")
            
            c3, c4, c5 = st.columns(3)
            new_dv = c3.selectbox("Đơn vị", ["Viên", "Vỉ", "Hộp", "Lọ", "Chai", "Gói", "Tuýp", "Cái"])
            new_ncc = c4.text_input("Nhà Cung Cấp")
            new_sl = c5.number_input("Số lượng ban đầu", min_value=1, value=10)
            
            c6, c7 = st.columns(2)
            new_gn = c6.number_input("Giá Nhập (VND)", min_value=0.0, step=1000.0)
            new_gb = c7.number_input("Giá Bán (VND)", min_value=0.0, step=1000.0)
            
            if st.form_submit_button("Thêm sản phẩm mới"):
                if new_ten:
                    # Kiểm tra trùng lặp cơ bản
                    is_duplicate = False
                    if not df_inv.empty:
                        if new_ma in df_inv['MaSanPham'].values.astype(str):
                            st.warning("⚠️ Mã sản phẩm này đã tồn tại! Hệ thống sẽ thêm hậu tố.")
                            new_ma = f"{new_ma}_{datetime.now().strftime('%M%S')}"

                    row = {
                        "MaSanPham": new_ma,
                        "TenSanPham": new_ten,
                        "DonVi": new_dv,
                        "NhaCungCap": new_ncc,
                        "SoLuong": new_sl,
                        "GiaNhap": new_gn,
                        "GiaBan": new_gb,
                        "ThanhTien": new_sl * new_gn
                    }
                    st.session_state['import_cart'].append(row)
                    st.success(f"Đã thêm sp mới: {new_ten}")
                    st.rerun()
                else:
                    st.error("Vui lòng nhập Tên sản phẩm!")

    # --- Danh sach cho nhap ---
    if st.session_state['import_cart']:
        st.divider()
        st.subheader("📝 Phiếu Nhập Kho (Preview)")
        df_imp = pd.DataFrame(st.session_state['import_cart'])
        
        st.dataframe(df_imp, use_container_width=True)
        
        total_imp = df_imp['ThanhTien'].sum()
        st.write(f"Tổng tiền nhập: **{format_currency(total_imp)}**")
        
        c_btn1, c_btn2 = st.columns(2)
        if c_btn1.button("Hủy bỏ"):
            st.session_state['import_cart'] = []
            st.rerun()
            
        if c_btn2.button("💾 LƯU VÀO KHO", type="primary"):
            with st.spinner("Đang nhập kho..."):
                if dm.process_import(st.session_state['import_cart']):
                    st.session_state['import_cart'] = []
                    st.balloons()
                    st.success("Nhập hàng thành công!")
                    st.rerun()

# --- 4. MAN HINH BAO CAO (REPORT) ---
def render_reports(df_inv):
    st.subheader("📊 Báo Cáo Kinh Doanh")
    
    tab1, tab2 = st.tabs(["📦 TỒN KHO & ĐỊNH GIÁ", "📈 HIỆU QUẢ KINH DOANH"])
    
    with tab1:
        if not df_inv.empty:
            df_view = df_inv.copy()
            df_view['TongTonGiaNhap'] = df_view['SoLuong'] * df_view['GiaNhap']
            df_view['TongTonGiaBan'] = df_view['SoLuong'] * df_view['GiaBan']
            
            m1, m2, m3 = st.columns(3)
            m1.metric("SKU (Mặt hàng)", len(df_view))
            m2.metric("Tổng vốn tồn", format_currency(df_view['TongTonGiaNhap'].sum()))
            m3.metric("Giá trị bán dự kiến", format_currency(df_view['TongTonGiaBan'].sum()))

            st.dataframe(df_view, use_container_width=True, height=500)
        else:
            st.info("Chưa có dữ liệu.")

    with tab2:
        df_sales = dm.load_sales_history()
        if df_sales.empty:
            st.info("Chưa có dữ liệu bán hàng.")
            return

        df_sales['NgayBan'] = pd.to_datetime(df_sales['NgayBan'])
        today = datetime.now()
        
        # Chart Doanh Thu Thang
        st.markdown(f"##### Doanh thu Tháng {today.month}/{today.year}")
        df_month = df_sales[(df_sales['NgayBan'].dt.month == today.month) & (df_sales['NgayBan'].dt.year == today.year)].copy()
        
        if not df_month.empty:
            df_month['Ngay'] = df_month['NgayBan'].dt.strftime('%d/%m')
            daily_stats = df_month.groupby('Ngay')[['ThanhTien', 'LoiNhuan']].sum().reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=daily_stats['Ngay'], y=daily_stats['ThanhTien'], name="Doanh Thu", marker_color='#3498DB'))
            fig.add_trace(go.Scatter(x=daily_stats['Ngay'], y=daily_stats['LoiNhuan'], name="Lợi Nhuận", line=dict(color='#E74C3C', width=3)))
            
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
            total_rev = df_month['ThanhTien'].sum()
            total_prof = df_month['LoiNhuan'].sum()
            
            c1, c2 = st.columns(2)
            c1.info(f"Tổng Doanh Thu Tháng: **{format_currency(total_rev)}**")
            c2.success(f"Tổng Lợi Nhuận Tháng: **{format_currency(total_prof)}**")
            
        else:
            st.warning("Tháng này chưa có doanh số.")

# --- MAIN APP ---
def main():
    if not st.session_state['is_logged_in']:
        render_login()
    else:
        # Load Data (Co Cache)
        df_inventory = dm.load_inventory()
        
        # --- Sidebar ---
        with st.sidebar:
            # Logo Sidebar
            if os.path.exists("assets/logo.png"):
                st.image("assets/logo.png", width=100)
            
            st.title("Admin Menu")
            menu = st.radio("Chọn chức năng:", 
                            ["Bán Hàng", "Nhập Hàng", "Báo Cáo"], 
                            index=0)
            
            st.markdown("---")
            if st.button("Đăng Xuất"):
                st.session_state['is_logged_in'] = False
                st.rerun()
            
            st.markdown("---")
            st.caption("Minh Châu Pharmacy System v2.0")

        # --- Header ---
        render_header()
        
        # --- Routing ---
        if menu == "Bán Hàng":
            render_sales(df_inventory)
        elif menu == "Nhập Hàng":
            render_import(df_inventory)
        elif menu == "Báo Cáo":
            render_reports(df_inventory)

if __name__ == "__main__":
    main()
