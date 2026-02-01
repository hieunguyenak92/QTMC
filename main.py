import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import data_manager as dm

# --- 1. CAU HINH GIAO DIEN (VẤN ĐỀ 1) ---
st.set_page_config(
    page_title="Minh Châu 24h", 
    layout="wide", 
    page_icon="assets/logo.png"
)

# Custom CSS giữ nguyên và bổ sung style cho Header
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

# --- RENDER HEADER (VẤN ĐỀ 1) ---
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

# --- 2. MAN HINH BAN HANG ---
def render_sales(df_inv):
    st.subheader("🛒 Bán Hàng Tại Quầy")
    col_search, col_cart = st.columns([5, 5], gap="large")
    
    with col_search:
        st.info("Tìm kiếm sản phẩm")
        if not df_inv.empty:
            df_inv['display_text'] = df_inv.apply(
                lambda x: f"{x['TenSanPham']} | Mã: {x['MaSanPham']} | Tồn: {x['SoLuong']} {x['DonVi']}", axis=1
            )
            options = [""] + df_inv['display_text'].tolist()
            selected_str = st.selectbox("🔍 Nhập tên hoặc mã:", options=options, key="search_box")
            
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

# --- 3. MAN HINH NHAP HANG (VẤN ĐỀ 2) ---
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
        # TỰ ĐỘNG LẤY MÃ (VẤN ĐỀ 2)
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

# --- 4. MAN HINH BAO CAO (BAO GỒM VẤN ĐỀ 3) ---
def render_reports(df_inv):
    st.subheader("📊 Báo Cáo Hệ Thống")
    t1, t2, t3 = st.tabs(["Tồn Kho & Giá Vốn", "Lợi Nhuận & Hoàn Trả", "Phân Tích Năm"])
    
    with t1:
        if not df_inv.empty:
            df_inv['GiaTriTon'] = df_inv['SoLuong'] * df_inv['GiaNhap']
            st.metric("Tổng vốn tồn kho", format_currency(df_inv['GiaTriTon'].sum()))
            st.dataframe(df_inv, use_container_width=True)
        else: st.info("Chưa có dữ liệu kho.")

    with t2:
        # VẤN ĐỀ 3: DANH SÁCH BÁN TRONG NGÀY
        st.write("### 📋 Danh sách hàng bán trong ngày")
        df_sales = dm.load_sales_history()
        
        if not df_sales.empty:
            # Fix KeyError bằng cách kiểm tra cột 'NgayBan'
            if 'NgayBan' in df_sales.columns:
                df_sales['NgayBan'] = pd.to_datetime(df_sales['NgayBan'])
                today = datetime.now().strftime('%Y-%m-%d')
                df_today = df_sales[df_sales['NgayBan'].dt.strftime('%Y-%m-%d') == today].copy()
                
                if not df_today.empty:
                    df_today = df_today.sort_values(by='NgayBan', ascending=False)
                    
                    # Hiển thị bảng có nút xóa/sửa
                    for idx, row in df_today.iterrows():
                        with st.container(border=True):
                            c1, c2, c3, c4, c5 = st.columns([1, 3, 1, 2, 1])
                            c1.write(f"🕒 {row['NgayBan'].strftime('%H:%M')}")
                            c2.write(f"**{row['TenSanPham']}** ({row['MaSanPham']})")
                            c3.write(f"{row['SoLuong']} {row['DonVi']}")
                            c4.write(f"Tổng: {format_currency(row['ThanhTien'])}")
                            
                            # Nút Hoàn trả (Xóa)
                            if c5.button("Hoàn trả", key=f"ret_{idx}"):
                                if dm.process_return(row['MaDonHang'], row['MaSanPham'], row['SoLuong']):
                                    st.success("Đã hoàn trả hàng vào kho!")
                                    st.rerun()
                else: st.info("Hôm nay chưa có đơn hàng nào.")

            st.divider()
            # Biểu đồ doanh thu tháng
            st.write("### 📈 Doanh thu & Lợi nhuận tháng này")
            df_month = df_sales[df_sales['NgayBan'].dt.month == datetime.now().month]
            if not df_month.empty:
                daily = df_month.groupby(df_month['NgayBan'].dt.day)[['ThanhTien', 'LoiNhuan']].sum()
                fig = go.Figure()
                fig.add_trace(go.Bar(x=daily.index, y=daily['ThanhTien'], name="Doanh Thu"))
                fig.add_trace(go.Scatter(x=daily.index, y=daily['LoiNhuan'], name="Lợi Nhuận", line=dict(color='red')))
                st.plotly_chart(fig, use_container_width=True)

    with t3:
        # PHẦN BÁO CÁO NĂM (GIỮ NGUYÊN CODE CŨ CỦA BẠN)
        st.write("### 🗓️ Phân tích hiệu quả theo năm")
        if not df_sales.empty:
            df_sales['Nam'] = df_sales['NgayBan'].dt.year
            df_sales['Thang'] = df_sales['NgayBan'].dt.month
            current_year = datetime.now().year
            df_year = df_sales[df_sales['Nam'] == current_year]
            
            if not df_year.empty:
                yearly_stats = df_year.groupby('Thang')[['ThanhTien', 'LoiNhuan']].sum().reset_index()
                # Chuyển đổi sang đơn vị Triệu để dễ nhìn như code cũ của bạn
                yearly_stats['DoanhThuTrieu'] = yearly_stats['ThanhTien'] / 1_000_000
                yearly_stats['LoiNhuanTrieu'] = yearly_stats['LoiNhuan'] / 1_000_000
                
                fig_year = go.Figure()
                fig_year.add_trace(go.Bar(x=yearly_stats['Thang'], y=yearly_stats['DoanhThuTrieu'], name="Doanh thu (Triệu)"))
                fig_year.add_trace(go.Scatter(x=yearly_stats['Thang'], y=yearly_stats['LoiNhuanTrieu'], name="Lợi nhuận (Triệu)", yaxis="y2", line=dict(color='#ff7f0e')))
                
                fig_year.update_layout(
                    yaxis=dict(title="Doanh thu"),
                    yaxis2=dict(title="Lợi nhuận", overlaying="y", side="right"),
                    legend=dict(x=0, y=1.1, orientation="h")
                )
                st.plotly_chart(fig_year, use_container_width=True)
            else: st.warning("Chưa có dữ liệu năm nay.")

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
