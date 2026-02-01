import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
import os
import data_manager as dm

# --- 1. CAU HINH GIAO DIEN ---
st.set_page_config(
    page_title="Minh Châu 24h", 
    layout="wide", 
    page_icon="assets/logo.png"
)

st.markdown("""
<style>
    .stButton>button {width: 100%; border-radius: 5px; height: 3em; font-weight: bold;}
    .reportview-container {background: #f0f2f6;}
    div[data-testid="stMetricValue"] {font-size: 1.2rem; color: #0068C9;}
    .header-title {
        font-size: 2.2em;
        font-weight: 700;
        color: #2E86C1;
        margin-bottom: 0px;
    }
    .header-subtitle {
        font-size: 1.1em;
        color: #555;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

# --- QUAN LY STATE ---
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False
if 'sales_cart' not in st.session_state:
    st.session_state['sales_cart'] = []
if 'import_cart' not in st.session_state:
    st.session_state['import_cart'] = []

# --- HAM HO TRO ---
def format_currency(amount):
    return f"{amount:,.0f} đ"

# --- RENDER HEADER ---
def render_header():
    c1, c2 = st.columns([1, 8])
    with c1:
        if os.path.exists("assets/logo.png"):
            st.image("assets/logo.png", width=90)
        else:
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
        st.subheader("🔒 Đăng Nhập Hệ Thống")
        with st.form("login_form"):
            password = st.text_input("Mật khẩu truy cập", type="password")
            submitted = st.form_submit_button("Truy cập ngay")
            if submitted:
                sys_pass = st.secrets.get("app_password", "123456")
                if password == sys_pass:
                    st.session_state['is_logged_in'] = True
                    st.rerun()
                else:
                    st.error("Sai mật khẩu!")

# --- 2. MAN HINH BAN HANG (THÊM SỬA GIÁ TẠM + XÓA TỪNG MÓN TRONG GIỎ) ---
def render_sales(df_inv):
    st.subheader("🛒 Bán Hàng Tại Quầy")
    col_search, col_cart = st.columns([5, 5], gap="large")
    
    with col_search:
        st.info("Tìm kiếm sản phẩm")
        if not df_inv.empty:
            search_term = st.text_input("🔍 Nhập tên hoặc mã sản phẩm", key="sales_search")
            
            filtered_df = df_inv
            if search_term:
                filtered_df = df_inv[
                    df_inv['TenSanPham'].str.contains(search_term, case=False, na=False) |
                    df_inv['MaSanPham'].str.contains(search_term, case=False, na=False)
                ]
            
            if not filtered_df.empty:
                options = filtered_df.apply(
                    lambda x: f"{x['TenSanPham']} | Mã: {x['MaSanPham']} | Tồn: {int(x['SoLuong'])} {x['DonVi']}", axis=1
                ).tolist()
                selected_str = st.selectbox("Chọn sản phẩm:", [""] + options, key="sales_select")
                
                if selected_str:
                    selected_item = filtered_df[
                        filtered_df.apply(
                            lambda x: f"{x['TenSanPham']} | Mã: {x['MaSanPham']} | Tồn: {int(x['SoLuong'])} {x['DonVi']}", axis=1
                        ) == selected_str
                    ].iloc[0]
                    
                    with st.container(border=True):
                        st.markdown(f"### {selected_item['TenSanPham']}")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Mã SP", selected_item['MaSanPham'])
                        c2.metric("Đơn vị", selected_item['DonVi'])
                        c3.metric("Tồn kho hiện tại", int(selected_item['SoLuong']))
                        
                        if selected_item['SoLuong'] < 10 and selected_item['SoLuong'] > 0:
                            st.warning(f"⚠️ Tồn kho thấp: chỉ còn {int(selected_item['SoLuong'])} {selected_item['DonVi']}! Nên nhập thêm.")
                        elif selected_item['SoLuong'] == 0:
                            st.error(f"🚨 Hết hàng: Tồn kho = 0!")
                        
                        st.divider()
                        
                        # THÊM TÍNH NĂNG 1: SỬA GIÁ BÁN TẠM THỜI (CHỈ CHO ĐƠN NÀY)
                        col_price_temp, col_qty = st.columns([1, 1])
                        default_price = float(selected_item['GiaBan'])
                        temp_price = col_price_temp.number_input("Giá bán tạm thời (đ)", min_value=0.0, value=default_price, step=1000.0, key=f"temp_price_{selected_item['MaSanPham']}")
                        qty_sell = col_qty.number_input("Số lượng mua:", min_value=1, value=1, step=1, key=f"qty_sell_{selected_item['MaSanPham']}")

                        # HIỆN FORM NHẬP NHANH KHI SL > TỒN
                        if qty_sell > selected_item['SoLuong']:
                            st.error(f"Không đủ tồn kho! Cần thêm ít nhất {qty_sell - selected_item['SoLuong']} {selected_item['DonVi']}.")
                            
                            st.markdown("#### 📦 Nhập nhanh bổ sung tồn kho ngay tại đây")
                            with st.form(key=f"quick_import_realtime_{selected_item['MaSanPham']}"):
                                col_q, col_gn, col_gb = st.columns(3)
                                suggested_qty = max(10, qty_sell - selected_item['SoLuong'])
                                quick_qty = col_q.number_input("Số lượng nhập thêm", min_value=1, value=suggested_qty)
                                quick_gn = col_gn.number_input("Giá nhập mới", value=float(selected_item['GiaNhap']))
                                quick_gb = col_gb.number_input("Giá bán mới (nếu thay đổi)", value=float(selected_item['GiaBan']))
                                
                                if st.form_submit_button("💾 Nhập nhanh & Thêm vào giỏ ngay", type="primary"):
                                    temp_import = [{
                                        "MaSanPham": selected_item['MaSanPham'],
                                        "TenSanPham": selected_item['TenSanPham'],
                                        "DonVi": selected_item['DonVi'],
                                        "SoLuong": quick_qty,
                                        "GiaNhap": quick_gn,
                                        "GiaBan": quick_gb,
                                        "NhaCungCap": ""
                                    }]
                                    
                                    if dm.process_import(temp_import):
                                        st.success(f"Đã nhập thêm {quick_qty} {selected_item['DonVi']} vào kho!")
                                        st.session_state['sales_cart'].append({
                                            "MaSanPham": selected_item['MaSanPham'],
                                            "TenSanPham": selected_item['TenSanPham'],
                                            "DonVi": selected_item['DonVi'],
                                            "GiaBan": temp_price,  # Dùng giá tạm
                                            "SoLuongBan": qty_sell,
                                            "ThanhTien": qty_sell * temp_price
                                        })
                                        st.toast("Đã thêm vào giỏ thành công!")
                                        st.rerun()

                        # NÚT THÊM VÀO GIỎ (DÙNG GIÁ TẠM)
                        if st.button("➕ Thêm vào giỏ", type="primary", key=f"add_normal_{selected_item['MaSanPham']}"):
                            if qty_sell <= selected_item['SoLuong']:
                                st.session_state['sales_cart'].append({
                                    "MaSanPham": selected_item['MaSanPham'],
                                    "TenSanPham": selected_item['TenSanPham'],
                                    "DonVi": selected_item['DonVi'],
                                    "GiaBan": temp_price,  # Giá tạm thời
                                    "SoLuongBan": qty_sell,
                                    "ThanhTien": qty_sell * temp_price
                                })
                                st.toast(f"Đã thêm {selected_item['TenSanPham']} vào giỏ với giá {format_currency(temp_price)}!")
                                st.rerun()
                            else:
                                st.error("Vui lòng nhập nhanh bổ sung tồn kho bên trên trước!")
            else:
                st.warning("Không tìm thấy sản phẩm nào.")
        else:
            st.warning("Kho hàng trống.")

    with col_cart:
        st.info("Giỏ hàng hiện tại")
        if st.session_state['sales_cart']:
            total_bill = 0
            # THÊM TÍNH NĂNG 2: XÓA TỪNG MÓN TRONG GIỎ
            for idx in range(len(st.session_state['sales_cart']) - 1, -1, -1):  # Duyệt ngược để xóa an toàn
                item = st.session_state['sales_cart'][idx]
                with st.container(border=True):
                    col_name, col_qty, col_price, col_total, col_del = st.columns([3, 1, 2, 2, 1])
                    col_name.write(f"**{item['TenSanPham']}** ({item['MaSanPham']})")
                    col_qty.write(f"{item['SoLuongBan']} {item['DonVi']}")
                    col_price.write(f"Giá: {format_currency(item['GiaBan'])}")
                    item_total = item['SoLuongBan'] * item['GiaBan']
                    col_total.write(f"**{format_currency(item_total)}**")
                    if col_del.button("🗑", key=f"del_{idx}"):
                        st.session_state['sales_cart'].pop(idx)
                        st.rerun()
                total_bill += item_total
            
            st.markdown(f"<h3 style='text-align: right; color: red;'>Tổng cộng: {format_currency(total_bill)}</h3>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button("🗑 Xóa toàn bộ giỏ"):
                st.session_state['sales_cart'] = []
                st.rerun()
            if c2.button("✅ THANH TOÁN", type="primary"):
                if dm.process_checkout(st.session_state['sales_cart']):
                    st.session_state['sales_cart'] = []
                    st.balloons()
                    st.success("Thanh toán thành công!")
                    st.rerun()
        else:
            st.caption("Chưa có hàng trong giỏ.")

# --- CÁC PHẦN CÒN LẠI GIỮ NGUYÊN (NHẬP HÀNG, BÁO CÁO VỚI LỊCH SỬ ĐƠN) ---
# (Tôi giữ nguyên phần render_import và render_reports như lần trước để code đầy đủ, không thiếu)

# ... (dán phần render_import và render_reports từ code lần trước ở đây, bao gồm lịch sử đơn hàng chi tiết)

# --- MAIN APP ---
# (giữ nguyên)

# --- 3. MAN HINH NHAP HANG ---
def render_import(df_inv):
    st.subheader("📦 Nhập hàng")
    tab1, tab2 = st.tabs(["Nhập thêm hàng cũ", "Thêm sản phẩm mới hoàn toàn"])
    
    with tab1:
        if not df_inv.empty:
            df_inv['imp_display'] = df_inv['TenSanPham'] + " (" + df_inv['MaSanPham'] + ")"
            sel = st.selectbox("Chọn SP:", [""] + df_inv['imp_display'].tolist())
            if sel:
                item = df_inv[df_inv['imp_display'] == sel].iloc[0]
                with st.form("f_old"):
                    c1, c2, c3 = st.columns(3)
                    q = c1.number_input("SL Nhập", 1, value=10)
                    p_in = c2.number_input("Giá Nhập", 0.0, value=float(item['GiaNhap']))
                    p_out = c3.number_input("Giá Bán", 0.0, value=float(item['GiaBan']))
                    if st.form_submit_button("Thêm vào phiếu"):
                        st.session_state['import_cart'].append({
                            "MaSanPham": item['MaSanPham'], "TenSanPham": item['TenSanPham'],
                            "DonVi": item['DonVi'], "SoLuong": q, "GiaNhap": p_in, "GiaBan": p_out
                        })
                        st.rerun()

    with tab2:
        next_id = len(df_inv) + 1 if not df_inv.empty else 1
        with st.form("f_new"):
            st.info(f"Gợi ý Mã SP tiếp theo: {next_id}")
            c1, c2 = st.columns([1, 2])
            m_id = c1.text_input("Mã SP (*)", value=str(next_id))
            m_ten = c2.text_input("Tên SP (*)")
            c3, c4, c5 = st.columns(3)
            m_dv = c3.selectbox("Đơn vị", ["Viên", "Vỉ", "Hộp", "Lọ", "Tuýp"])
            m_ncc = c4.text_input("Nhà cung cấp")
            m_sl = c5.number_input("SL ban đầu", 1, value=1)
            c6, c7 = st.columns(2)
            m_gn = c6.number_input("Giá Nhập", 0.0)
            m_gb = c7.number_input("Giá Bán", 0.0)
            if st.form_submit_button("Xác nhận SP mới"):
                if m_ten:
                    st.session_state['import_cart'].append({
                        "MaSanPham": m_id, "TenSanPham": m_ten, "DonVi": m_dv,
                        "NhaCungCap": m_ncc, "SoLuong": m_sl, "GiaNhap": m_gn, "GiaBan": m_gb
                    })
                    st.rerun()

    if st.session_state['import_cart']:
        st.divider()
        st.write("### Danh sách chờ nhập tồn kho")
        df_imp = pd.DataFrame(st.session_state['import_cart'])
        st.table(df_imp)
        if st.button("💾 LƯU TẤT CẢ VÀO KHO", type="primary"):
            if dm.process_import(st.session_state['import_cart']):
                st.session_state['import_cart'] = []
                st.success("Đã nhập tồn kho thành công!")
                st.rerun()

# --- 4. MAN HINH BAO CAO (THÊM LỊCH SỬ ĐƠN HÀNG CHI TIẾT THEO NGÀY) ---
def render_reports(df_inv):
    st.subheader("📊 Báo Cáo Hệ Thống")
    
    df_sales = dm.load_sales_history()
    
    if not df_sales.empty:
        total_revenue = df_sales['ThanhTien'].sum()
        total_profit = df_sales['LoiNhuan'].sum()
        c1, c2 = st.columns(2)
        c1.metric("Tổng doanh thu toàn thời gian", format_currency(total_revenue))
        c2.metric("Tổng lợi nhuận gộp toàn thời gian", format_currency(total_profit))
    st.divider()
    
    t1, t2, t3 = st.tabs(["Tồn Kho & Giá Vốn", "Lợi Nhuận & Hoàn Trả", "Phân Tích Năm"])
    
    with t1:
        if not df_inv.empty:
            df_inv['GiaTriTon'] = df_inv['SoLuong'] * df_inv['GiaNhap']
            st.metric("Tổng vốn tồn kho", format_currency(df_inv['GiaTriTon'].sum()))
            st.dataframe(df_inv, use_container_width=True)
            
            st.write("### ⚠️ Sản phẩm sắp hết (dưới 10 đơn vị)")
            low_stock = df_inv[df_inv['SoLuong'] < 10]
            if not low_stock.empty:
                st.dataframe(low_stock[['MaSanPham', 'TenSanPham', 'SoLuong', 'DonVi']], use_container_width=True)
            else:
                st.success("Tất cả sản phẩm đều đủ tồn kho!")
        else: 
            st.info("Chưa có dữ liệu kho.")

    with t2:
        # Metric hôm nay
       if not df_sales.empty and 'NgayBan' in df_sales.columns:
            df_sales['NgayBan'] = pd.to_datetime(df_sales['NgayBan'], errors='coerce')
            today_str = datetime.now().strftime('%Y-%m-%d')
            df_today_sales = df_sales[(df_sales['NgayBan'].dt.strftime('%Y-%m-%d') == today_str) & (df_sales['SoLuong'] > 0)]
            
            today_revenue = df_today_sales['ThanhTien'].sum()
            today_profit = df_today_sales['LoiNhuan'].sum()
            today_orders = df_today_sales['MaDonHang'].nunique()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Doanh thu hôm nay", format_currency(today_revenue))
            col2.metric("Lợi nhuận hôm nay", format_currency(today_profit))
            col3.metric("Số đơn hàng hôm nay", today_orders)
            st.divider()
    
        # LỊCH SỬ CHI TIẾT ĐƠN HÀNG VỚI NÚT HOÀN TRẢ TỪNG MÓN
        st.write("### 📋 Lịch sử chi tiết đơn hàng (có thể hoàn trả từng món)")
        selected_date = st.date_input("Chọn ngày xem đơn hàng", value=date.today())
        
        if not df_sales.empty and 'NgayBan' in df_sales.columns:
            df_sales['date'] = df_sales['NgayBan'].dt.date
            df_selected_day = df_sales[df_sales['date'] == selected_date].copy()
            
            if not df_selected_day.empty:
                day_revenue = df_selected_day[df_selected_day['SoLuong'] > 0]['ThanhTien'].sum()
                st.info(f"**Tổng doanh thu ngày {selected_date.strftime('%d/%m/%Y')}: {format_currency(day_revenue)}**")
                
                orders = df_selected_day.groupby('MaDonHang')
                
                for order_id, order_df in orders:
                    order_time = order_df['NgayBan'].min().strftime('%H:%M')
                    order_total = order_df[order_df['SoLuong'] > 0]['ThanhTien'].sum()
                    num_items = len(order_df[order_df['SoLuong'] > 0])
                    
                    with st.expander(f"🧾 Đơn {order_id} | {order_time} | {num_items} sản phẩm | Tổng: {format_currency(order_total)}"):
                        for idx, row in order_df.iterrows():
                            if row['SoLuong'] > 0:
                                with st.container(border=True):
                                    c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 2, 1])
                                    c1.write(f"**{row['TenSanPham']}** ({row['MaSanPham']})")
                                    c2.write(f"{int(row['SoLuong'])} {row['DonVi']}")
                                    c3.write(f"Giá: {format_currency(row['GiaBan'])}")
                                    c4.write(f"Thành tiền: {format_currency(row['ThanhTien'])}")
                                    if c5.button("Hoàn trả", key=f"ret_{idx}_{order_id}"):
                                        if dm.process_return(row['MaDonHang'], row['MaSanPham'], row['SoLuong']):
                                            st.success(f"Đã hoàn trả {row['TenSanPham']} thành công!")
                                            st.rerun()
            else:
                st.info(f"Ngày {selected_date.strftime('%d/%m/%Y')} chưa có đơn hàng nào.")
        else:
            st.info("Chưa có dữ liệu bán hàng.")
        
        st.divider()
        # THÊM TÍNH NĂNG MỚI: LỊCH SỬ ĐƠN HÀNG CHI TIẾT THEO NGÀY
        st.write("### 📋 Lịch sử chi tiết đơn hàng")
        selected_date = st.date_input("Chọn ngày xem đơn hàng", value=date.today())
        
        if not df_sales.empty and 'NgayBan' in df_sales.columns:
            df_sales['date'] = df_sales['NgayBan'].dt.date
            df_selected_day = df_sales[df_sales['date'] == selected_date].copy()
            
            if not df_selected_day.empty:
                # Tổng doanh thu ngày chọn
                day_revenue = df_selected_day[df_selected_day['SoLuong'] > 0]['ThanhTien'].sum()
                st.info(f"**Tổng doanh thu ngày {selected_date.strftime('%d/%m/%Y')}: {format_currency(day_revenue)}**")
                
                # Group theo đơn hàng
                orders = df_selected_day.groupby('MaDonHang')
                
                for order_id, order_df in orders:
                    order_time = order_df['NgayBan'].min().strftime('%H:%M')
                    order_total = order_df['ThanhTien'].sum()
                    num_items = len(order_df)
                    
                    with st.expander(f"🧾 Đơn {order_id} | {order_time} | {num_items} sản phẩm | Tổng: {format_currency(order_total)}"):
                        # Chỉ hiển thị các row bán (SoLuong > 0), bỏ hoàn trả
                        display_df = order_df[order_df['SoLuong'] > 0][['TenSanPham', 'SoLuong', 'DonVi', 'GiaBan', 'ThanhTien']]
                        display_df['Thành tiền'] = display_df['ThanhTien'].apply(format_currency)
                        display_df['Giá bán'] = display_df['GiaBan'].apply(format_currency)
                        st.dataframe(display_df[['TenSanPham', 'SoLuong', 'DonVi', 'Giá bán', 'Thành tiền']], use_container_width=True, hide_index=True)
            else:
                st.info(f"Ngày {selected_date.strftime('%d/%m/%Y')} chưa có đơn hàng nào.")
        else:
            st.info("Chưa có dữ liệu bán hàng.")
        
        st.divider()
        
        df_month = df_sales[df_sales['NgayBan'].dt.month == datetime.now().month].copy() if not df_sales.empty and 'NgayBan' in df_sales.columns else pd.DataFrame()
        if not df_month.empty:
            st.write("### 🔥 Top 10 sản phẩm bán chạy tháng này")
            top10 = df_month[df_month['SoLuong'] > 0].groupby(['MaSanPham', 'TenSanPham'])['SoLuong'].sum().reset_index()
            top10 = top10.sort_values('SoLuong', ascending=False).head(10)
            st.dataframe(top10, use_container_width=True)
            
            st.write("### 📊 Doanh thu theo sản phẩm (Top 10 tháng này)")
            top10_revenue = df_month[df_month['SoLuong'] > 0].groupby('TenSanPham')['ThanhTien'].sum().reset_index()
            top10_revenue = top10_revenue.sort_values('ThanhTien', ascending=False).head(10)
            fig_prod = go.Figure(go.Bar(
                x=top10_revenue['ThanhTien'],
                y=top10_revenue['TenSanPham'],
                orientation='h',
                marker_color='#0068C9'
            ))
            fig_prod.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Doanh thu (đ)", height=400)
            st.plotly_chart(fig_prod, use_container_width=True)
            
            st.write("### 🔥 Top 10 sản phẩm bán chạy toàn thời gian")
            top10_all = df_sales[df_sales['SoLuong'] > 0].groupby(['MaSanPham', 'TenSanPham'])['SoLuong'].sum().reset_index()
            top10_all = top10_all.sort_values('SoLuong', ascending=False).head(10)
            st.dataframe(top10_all, use_container_width=True)
        
        st.write("### 📈 Doanh thu & Lợi nhuận tháng này")
        if not df_month.empty:
            current_month = datetime.now().month
            current_year = datetime.now().year
            last_day = datetime.now().day

            daily_full = pd.DataFrame({'day': list(range(1, last_day + 1))})

            daily_group = df_month.groupby(df_month['NgayBan'].dt.day)[['ThanhTien', 'LoiNhuan']].sum().reset_index()
            daily_group.rename(columns={'NgayBan': 'day'}, inplace=True)

            daily = daily_full.merge(daily_group, on='day', how='left').fillna(0)
            daily['day'] = daily['day'].astype(int)
            daily['ThanhTien'] = daily['ThanhTien'].clip(lower=0)
            daily['LoiNhuan'] = daily['LoiNhuan'].clip(lower=0)

            max_y_value = max(daily['ThanhTien'].max(), daily['LoiNhuan'].max())
            if max_y_value == 0:
                max_y_value = 100000
            max_y = max_y_value * 1.15

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=daily['day'],
                y=daily['ThanhTien'],
                name="Doanh Thu",
                marker_color='#0068C9',
                width=0.8
            ))
            fig.add_trace(go.Scatter(
                x=daily['day'],
                y=daily['LoiNhuan'],
                name="Lợi Nhuận",
                mode='lines+markers',
                line=dict(color='red', width=3),
                marker=dict(size=8)
            ))

            fig.update_layout(
                title=f"Doanh thu & Lợi nhuận tháng {current_month}/{current_year}",
                xaxis_title="Ngày",
                yaxis_title="Số tiền (đ)",
                xaxis=dict(
                    type='category',
                    tickmode='linear',
                    range=[0.5, last_day + 0.5],
                    constrain='domain',
                    showgrid=False
                ),
                yaxis=dict(
                    range=[0, max_y],
                    fixedrange=True,
                    zeroline=False,
                    showgrid=True
                ),
                bargap=0.15,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Tháng này chưa có dữ liệu bán hàng.")

    with t3:
        st.write("### 🗓️ Phân tích hiệu quả theo năm")
        if not df_sales.empty:
            df_sales['Nam'] = df_sales['NgayBan'].dt.year
            df_sales['Thang'] = df_sales['NgayBan'].dt.month
            current_year = datetime.now().year
            df_year = df_sales[df_sales['Nam'] == current_year].copy()
            
            if not df_year.empty:
                yearly_stats = df_year.groupby('Thang')[['ThanhTien', 'LoiNhuan']].sum().reset_index()
                months_full = pd.DataFrame({'Thang': range(1, 13)})
                yearly_stats = months_full.merge(yearly_stats, on='Thang', how='left').fillna(0)
                yearly_stats['DoanhThuTrieu'] = (yearly_stats['ThanhTien'] / 1_000_000).clip(lower=0)
                yearly_stats['LoiNhuanTrieu'] = (yearly_stats['LoiNhuan'] / 1_000_000).clip(lower=0)

                fig_year = go.Figure()
                fig_year.add_trace(go.Bar(x=yearly_stats['Thang'], y=yearly_stats['DoanhThuTrieu'], name="Doanh thu (Triệu)", marker_color='#0068C9'))
                fig_year.add_trace(go.Scatter(x=yearly_stats['Thang'], y=yearly_stats['LoiNhuanTrieu'], name="Lợi nhuận (Triệu)", mode='lines+markers', yaxis="y2", line=dict(color='#ff7f0e', width=3)))
                fig_year.update_layout(
                    title=f"Doanh thu & Lợi nhuận năm {current_year}",
                    xaxis_title="Tháng",
                    yaxis=dict(title="Doanh thu (Triệu đ)", range=[0, None]),
                    yaxis2=dict(title="Lợi nhuận (Triệu đ)", overlaying="y", side="right", range=[0, None]),
                    xaxis=dict(type='category')
                )
                st.plotly_chart(fig_year, use_container_width=True)
            else:
                st.warning("Chưa có dữ liệu năm nay.")
        else:
            st.info("Chưa có dữ liệu bán hàng.")

# --- MAIN APP ---
def main():
    if not st.session_state['is_logged_in']:
        render_login()
    else:
        df_inventory = dm.load_inventory()
        
        with st.sidebar:
            if os.path.exists("assets/logo.png"):
                st.image("assets/logo.png", width=120)
            st.title("Hệ Thống Quản Lý")
            menu = st.radio("Chức năng chính", ["Bán Hàng", "Nhập Hàng", "Báo Cáo"], index=0)
            st.divider()
            if st.button("Đăng Xuất"):
                st.session_state['is_logged_in'] = False
                st.rerun()
            st.caption("Minh Châu 24h v2.5")

        render_header()
        
        if menu == "Bán Hàng":
            render_sales(df_inventory)
        elif menu == "Nhập Hàng":
            render_import(df_inventory)
        elif menu == "Báo Cáo":
            render_reports(df_inventory)

if __name__ == "__main__":
    main()
