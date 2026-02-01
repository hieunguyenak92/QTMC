import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
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

# --- 2. MAN HINH BAN HANG (GIỮ NGUYÊN + TÌM KIẾM CẢI THIỆN) ---
def render_sales(df_inv):
    st.subheader("🛒 Bán Hàng Tại Quầy")
    col_search, col_cart = st.columns([5, 5], gap="large")
    
    with col_search:
        st.info("Tìm kiếm sản phẩm")
        if not df_inv.empty:
            search_term = st.text_input("🔍 Nhập tên hoặc mã sản phẩm")
            
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
                selected_str = st.selectbox("Chọn sản phẩm:", [""] + options)
                
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
                        c3.metric("Tồn kho", int(selected_item['SoLuong']))
                        st.divider()
                        c_price, c_qty = st.columns([1, 1])
                        c_price.metric("Giá bán", format_currency(selected_item['GiaBan']))
                        qty_sell = c_qty.number_input("Số lượng mua:", min_value=1, value=1, step=1)
                        
                        if st.button("➕ Thêm vào giỏ", type="primary"):
                            if qty_sell > selected_item['SoLuong']:
                                st.error(f"Không đủ tồn kho!")
                            else:
                                st.session_state['sales_cart'].append({
                                    "MaSanPham": selected_item['MaSanPham'],
                                    "TenSanPham": selected_item['TenSanPham'],
                                    "DonVi": selected_item['DonVi'],
                                    "GiaBan": float(selected_item['GiaBan']),
                                    "SoLuongBan": qty_sell,
                                    "ThanhTien": qty_sell * selected_item['GiaBan']
                                })
                                st.toast(f"Đã thêm {selected_item['TenSanPham']}")
            else:
                st.warning("Không tìm thấy sản phẩm nào.")
        else:
            st.warning("Kho hàng trống.")

    with col_cart:
        st.info("Giỏ hàng hiện tại")
        if st.session_state['sales_cart']:
            df_cart = pd.DataFrame(st.session_state['sales_cart'])
            st.dataframe(df_cart[['TenSanPham', 'SoLuongBan', 'ThanhTien']], use_container_width=True, hide_index=True)
            
            total_bill = df_cart['ThanhTien'].sum()
            st.markdown(f"<h3 style='text-align: right; color: red;'>Tổng: {format_currency(total_bill)}</h3>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button("🗑 Xóa giỏ"):
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

# --- 3. MAN HINH NHAP HANG (GIỮ NGUYÊN) ---
def render_import(df_inv):
    st.subheader("📦 Nhập Kho")
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
        st.write("### Danh sách chờ nhập kho")
        df_imp = pd.DataFrame(st.session_state['import_cart'])
        st.table(df_imp)
        if st.button("💾 LƯU TẤT CẢ VÀO KHO", type="primary"):
            if dm.process_import(st.session_state['import_cart']):
                st.session_state['import_cart'] = []
                st.success("Đã nhập kho thành công!")
                st.rerun()

# --- 4. MAN HINH BAO CAO (FIX BIỂU ĐỒ THÁNG + THÊM NHIỀU TÍNH NĂNG MỚI) ---
def render_reports(df_inv):
    st.subheader("📊 Báo Cáo Hệ Thống")
    
    df_sales = dm.load_sales_history()
    
    # Tổng doanh thu & lợi nhuận toàn thời gian
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
        # THÊM: Doanh thu hôm nay (metric nổi bật)
        if not df_sales.empty and 'NgayBan' in df_sales.columns:
            df_sales['NgayBan'] = pd.to_datetime(df_sales['NgayBan'])
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

        st.write("### 📋 Danh sách hàng bán trong ngày")
        if not df_sales.empty and 'NgayBan' in df_sales.columns:
            today = datetime.now().strftime('%Y-%m-%d')
            df_today = df_sales[df_sales['NgayBan'].dt.strftime('%Y-%m-%d') == today].copy()
            
            if not df_today.empty:
                df_today = df_today.sort_values(by='NgayBan', ascending=False)
                for idx, row in df_today.iterrows():
                    with st.container(border=True):
                        c1, c2, c3, c4, c5 = st.columns([1, 3, 1, 2, 1])
                        c1.write(f"🕒 {row['NgayBan'].strftime('%H:%M')}")
                        c2.write(f"**{row['TenSanPham']}** ({row['MaSanPham']})")
                        c3.write(f"{int(row['SoLuong'])} {row['DonVi']}")
                        c4.write(f"Tổng: {format_currency(row['ThanhTien'])}")
                        if row['SoLuong'] > 0:
                            if c5.button("Hoàn trả", key=f"ret_{idx}"):
                                if dm.process_return(row['MaDonHang'], row['MaSanPham'], row['SoLuong']):
                                    st.success("Đã hoàn trả hàng vào kho!")
                                    st.rerun()
            else:
                st.info("Hôm nay chưa có đơn hàng nào.")
        
        st.divider()
        
        df_month = df_sales[df_sales['NgayBan'].dt.month == datetime.now().month].copy()
        if not df_month.empty:
            # THÊM: Top 10 bán chạy tháng này (giữ nguyên cũ)
            st.write("### 🔥 Top 10 sản phẩm bán chạy tháng này")
            top10 = df_month[df_month['SoLuong'] > 0].groupby(['MaSanPham', 'TenSanPham'])['SoLuong'].sum().reset_index()
            top10 = top10.sort_values('SoLuong', ascending=False).head(10)
            st.dataframe(top10, use_container_width=True)
            
            # THÊM: Biểu đồ doanh thu theo sản phẩm top 10 tháng này
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
            
            # THÊM: Top 10 bán chạy toàn thời gian
            st.write("### 🔥 Top 10 sản phẩm bán chạy toàn thời gian")
            top10_all = df_sales[df_sales['SoLuong'] > 0].groupby(['MaSanPham', 'TenSanPham'])['SoLuong'].sum().reset_index()
            top10_all = top10_all.sort_values('SoLuong', ascending=False).head(10)
            st.dataframe(top10_all, use_container_width=True)
        
        # FIX DỨT ĐIỂM BIỂU ĐỒ THÁNG
        st.write("### 📈 Doanh thu & Lợi nhuận tháng này")
        if not df_month.empty:
            current_year = datetime.now().year
            current_month = datetime.now().month
            last_day = datetime.now().day
            
            # Tạo full ngày 1 -> hôm nay
            days_in_month = pd.date_range(
                start=f"{current_year}-{current_month:02d}-01",
                end=datetime.now().strftime('%Y-%m-%d'),
                freq='D'
            )
            daily_full = pd.DataFrame({'day': days_in_month.dt.day})

            # Group data
            daily = df_month.groupby(df_month['NgayBan'].dt.day)[['ThanhTien', 'LoiNhuan']].sum().reset_index()
            daily.rename(columns={'NgayBan': 'day'}, inplace=True)

            # Merge + fill 0 + ép int
            daily = daily_full.merge(daily, on='day', how='left').fillna(0)
            daily['day'] = daily['day'].astype(int)
            daily['ThanhTien'] = daily['ThanhTien'].clip(lower=0)
            daily['LoiNhuan'] = daily['LoiNhuan'].clip(lower=0)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=daily['day'],
                y=daily['ThanhTien'],
                name="Doanh Thu",
                marker_color='#0068C9'
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
                yaxis=dict(range=[0, None]),
                xaxis=dict(type='category', tickmode='linear')  # FIX CHÍNH: trục x category + linear
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
