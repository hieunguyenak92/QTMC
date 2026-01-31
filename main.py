import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import data_manager as dm

# --- CAU HINH GIAO DIEN ---
st.set_page_config(page_title="Nhà Thuốc 4.0", layout="wide", page_icon="💊")

# Custom CSS de giao dien gon gang hon
st.markdown("""
<style>
    .stButton>button {width: 100%; border-radius: 5px; height: 3em;}
    .reportview-container {background: #f0f2f6;}
    div[data-testid="stMetricValue"] {font-size: 1.2rem;}
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

# --- 1. MAN HINH DANG NHAP ---
def render_login():
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.title("🔒 Đăng Nhập")
        password = st.text_input("Mật khẩu hệ thống", type="password")
        if st.button("Truy cập"):
            # Mat khau cau hinh trong secrets hoac mac dinh
            sys_pass = st.secrets.get("app_password", "123456")
            if password == sys_pass:
                st.session_state['is_logged_in'] = True
                st.rerun()
            else:
                st.error("Sai mật khẩu!")

# --- 2. MAN HINH BAN HANG (POS) ---
def render_sales(df_inv):
    st.header("💊 Bán Hàng Tại Quầy")
    
    col_search, col_cart = st.columns([4, 6], gap="large")
    
    with col_search:
        st.subheader("1. Tìm kiếm & Chọn hàng")
        # Yeu cau: Tim kiem hien thi ten + ton kho
        if not df_inv.empty:
            # Tao cot search_key de hien thi trong dropdown
            df_inv['display_text'] = df_inv.apply(
                lambda x: f"{x['TenSanPham']} | Mã: {x['MaSanPham']} | Tồn: {x['SoLuong']} {x['DonVi']}", 
                axis=1
            )
            
            # Selectbox dong vai tro thanh tim kiem thong minh
            options = [""] + df_inv['display_text'].tolist()
            selected_str = st.selectbox("🔍 Nhập tên hoặc mã sản phẩm:", options=options)
            
            if selected_str:
                # Parse lay thong tin san pham da chon
                selected_item = df_inv[df_inv['display_text'] == selected_str].iloc[0]
                
                with st.container(border=True):
                    st.info(f"Đang chọn: **{selected_item['TenSanPham']}**")
                    
                    c1, c2 = st.columns(2)
                    c1.write(f"Đơn vị: **{selected_item['DonVi']}**")
                    c1.write(f"Tồn kho: **{selected_item['SoLuong']}**")
                    c2.metric("Giá bán", format_currency(selected_item['GiaBan']))
                    
                    # Form nhap so luong
                    qty_sell = st.number_input("Số lượng bán:", min_value=1, value=1)
                    
                    # Tinh thanh tien tu dong
                    temp_total = qty_sell * selected_item['GiaBan']
                    st.write(f"Thành tiền: :red[**{format_currency(temp_total)}**]")
                    
                    if st.button("➕ Thêm vào giỏ hàng", type="primary"):
                        if qty_sell > selected_item['SoLuong']:
                            st.warning("⚠️ Không đủ hàng tồn kho để bán!")
                        else:
                            # Them vao gio hang
                            item = {
                                "MaSanPham": selected_item['MaSanPham'],
                                "TenSanPham": selected_item['TenSanPham'],
                                "DonVi": selected_item['DonVi'],
                                "GiaBan": float(selected_item['GiaBan']),
                                "SoLuongBan": qty_sell,
                                "ThanhTien": temp_total
                            }
                            st.session_state['sales_cart'].append(item)
                            st.success("Đã thêm!")
                            st.rerun()
        else:
            st.warning("Kho hàng đang trống. Vui lòng nhập hàng trước.")

    with col_cart:
        st.subheader("2. Chi tiết đơn hàng")
        cart = st.session_state['sales_cart']
        
        if cart:
            total_bill = 0
            
            # Hien thi danh sach dang bang co nut xoa (Hack UI bang columns)
            # Header
            h1, h2, h3, h4, h5 = st.columns([3, 1, 2, 2, 1])
            h1.markdown("**Tên SP**")
            h2.markdown("**SL**")
            h3.markdown("**Đơn giá**")
            h4.markdown("**Thành tiền**")
            h5.markdown("**Xóa**")
            st.divider()
            
            # Loop render tung dong
            for i, item in enumerate(cart):
                c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 2, 1])
                c1.write(item['TenSanPham'])
                c2.write(item['SoLuongBan'])
                c3.write(f"{item['GiaBan']:,.0f}")
                c4.write(f"{item['ThanhTien']:,.0f}")
                
                # Yeu cau: Nut X de xoa san pham neu nhap nham
                if c5.button("❌", key=f"del_{i}"):
                    st.session_state['sales_cart'].pop(i)
                    st.rerun()
                
                total_bill += item['ThanhTien']
            
            st.divider()
            # Footer Thanh Toan
            col_total, col_btn = st.columns([1, 1])
            col_total.markdown(f"### Tổng thanh toán: :red[{format_currency(total_bill)}]")
            
            if col_btn.button("💾 LƯU & XUẤT HÓA ĐƠN", type="primary", use_container_width=True):
                with st.spinner("Đang trừ kho và lưu báo cáo..."):
                    success = dm.process_checkout(cart)
                    if success:
                        st.session_state['sales_cart'] = []
                        st.success("✅ Đã lưu thành công!")
                        st.cache_data.clear() # Xoa cache de load lai ton kho moi
                        st.rerun()
                    else:
                        st.error("Lưu thất bại. Vui lòng kiểm tra kết nối.")
        else:
            st.info("Chưa có sản phẩm nào trong giỏ.")

# --- 3. MAN HINH NHAP HANG (IMPORT) ---
def render_import(df_inv):
    st.header("📦 Nhập Sản Phẩm")
    
    # Chia lam 2 tab ro rang: Nhap hang cu va Them hang moi
    tab1, tab2 = st.tabs(["NHẬP HÀNG CÓ SẴN", "THÊM SẢN PHẨM MỚI"])
    
    # --- Tab 1: Hang co san ---
    with tab1:
        if not df_inv.empty:
            df_inv['imp_display'] = df_inv.apply(lambda x: f"{x['TenSanPham']} - {x['MaSanPham']}", axis=1)
            options_imp = [""] + df_inv['imp_display'].tolist()
            
            sel_item = st.selectbox("Chọn hàng để nhập thêm:", options=options_imp)
            
            if sel_item:
                # Lay thong tin cu
                curr_item = df_inv[df_inv['imp_display'] == sel_item].iloc[0]
                
                with st.form("form_add_stock"):
                    c1, c2, c3 = st.columns(3)
                    qty_in = c1.number_input("Số lượng nhập", min_value=1, value=10)
                    price_in = c2.number_input("Giá nhập mới", min_value=0.0, value=float(curr_item['GiaNhap']))
                    price_out = c3.number_input("Giá bán mới", min_value=0.0, value=float(curr_item['GiaBan']))
                    
                    if st.form_submit_button("Thêm vào phiếu nhập"):
                        row = {
                            "MaSanPham": curr_item['MaSanPham'],
                            "TenSanPham": curr_item['TenSanPham'],
                            "DonVi": curr_item['DonVi'],
                            "NhaCungCap": curr_item['NhaCungCap'],
                            "SoLuong": qty_in,
                            "GiaNhap": price_in,
                            "GiaBan": price_out,
                            "ThanhTien": qty_in * price_in
                        }
                        st.session_state['import_cart'].append(row)
                        st.success("Đã thêm vào danh sách chờ")
                        st.rerun()
        else:
            st.warning("Kho trống, hãy dùng tab 'Thêm Sản Phẩm Mới'.")

    # --- Tab 2: Them moi hoan toan ---
    with tab2:
        st.write("Dùng cho sản phẩm lần đầu tiên nhập về nhà thuốc.")
        with st.form("form_new_product"):
            c1, c2 = st.columns(2)
            new_ma = c1.text_input("Mã Sản Phẩm (*Bắt buộc)")
            new_ten = c2.text_input("Tên Sản Phẩm (*Bắt buộc)")
            
            c3, c4, c5 = st.columns(3)
            new_dv = c3.selectbox("Đơn vị", ["Viên", "Vỉ", "Hộp", "Lọ", "Chai", "Gói", "Tuýp", "Cái"])
            new_ncc = c4.text_input("Nhà Cung Cấp")
            new_sl = c5.number_input("Số lượng ban đầu", min_value=1)
            
            c6, c7 = st.columns(2)
            new_gn = c6.number_input("Giá Nhập (VND)", min_value=0.0, step=1000.0)
            new_gb = c7.number_input("Giá Bán (VND)", min_value=0.0, step=1000.0)
            
            if st.form_submit_button("Thêm sản phẩm mới"):
                if new_ma and new_ten:
                    # Logic: Kiem tra trung ma trong Session list
                    # (Thuc te se check DB khi Luu)
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
                    st.success("Đã thêm sản phẩm mới vào danh sách chờ")
                    st.rerun()
                else:
                    st.error("Thiếu Mã hoặc Tên sản phẩm!")

    # --- Danh sach cho nhap ---
    st.divider()
    if st.session_state['import_cart']:
        st.subheader("Danh sách chuẩn hàng nhập ")
        df_imp = pd.DataFrame(st.session_state['import_cart'])
        
        st.dataframe(df_imp, use_container_width=True)
        st.write(f"Tổng tiền nhập dự kiến: **{format_currency(df_imp['ThanhTien'].sum())}**")
        
        btn_col1, btn_col2 = st.columns(2)
        if btn_col1.button("Hủy bỏ tất cả"):
            st.session_state['import_cart'] = []
            st.rerun()
            
        if btn_col2.button("💾 LƯU VÀO KHO", type="primary"):
            with st.spinner("Đang nhập tồn kho..."):
                if dm.process_import(st.session_state['import_cart']):
                    st.session_state['import_cart'] = []
                    st.success("Nhập hàng thành công!")
                    st.cache_data.clear()
                    st.rerun()

# --- 4. MAN HINH BAO CAO (REPORT) ---
def render_reports(df_inv):
    st.header("📊 Hệ Thống Báo Cáo Chuyên Sâu")
    
    tab1, tab2 = st.tabs(["📦 BÁO CÁO TỒN KHO", "📈 BÁO CÁO LÃI LỖ"])
    
    with tab1:
        st.subheader("Chi tiết tồn kho hiện tại")
        if not df_inv.empty:
            df_view = df_inv.copy()
            df_view['TongTonGiaNhap'] = df_view['SoLuong'] * df_view['GiaNhap']
            df_view['TongTonGiaBan'] = df_view['SoLuong'] * df_view['GiaBan']
            
            # Metric nhanh
            m1, m2, m3 = st.columns(3)
            m1.metric("Tổng mặt hàng", len(df_view))
            m2.metric("Vốn tồn kho", format_currency(df_view['TongTonGiaNhap'].sum()))
            m3.metric("Giá trị niêm yết", format_currency(df_view['TongTonGiaBan'].sum()))

            st.dataframe(
                df_view[['MaSanPham', 'TenSanPham', 'DonVi', 'SoLuong', 'GiaNhap', 'GiaBan', 'TongTonGiaNhap', 'TongTonGiaBan']],
                use_container_width=True, height=400
            )
        else:
            st.info("Chưa có dữ liệu tồn kho.")

    with tab2:
        df_sales = dm.load_sales_history()
        if df_sales.empty:
            st.info("Chưa có dữ liệu bán hàng để lập báo cáo lãi lỗ.")
            return

        # --- XỬ LÝ DỮ LIỆU THỜI GIAN ---
        df_sales['NgayBan'] = pd.to_datetime(df_sales['NgayBan'])
        today = datetime.now()
        
        # 1. Báo cáo Tháng Hiện Tại (Theo từng ngày)
        st.subheader(f"1. Doanh thu & Lợi nhuận Tháng {today.month}/{today.year}")
        df_month = df_sales[(df_sales['NgayBan'].dt.month == today.month) & (df_sales['NgayBan'].dt.year == today.year)].copy()
        
        if not df_month.empty:
            df_month['Ngay'] = df_month['NgayBan'].dt.strftime('%d/%m')
            daily_stats = df_month.groupby('Ngay')[['ThanhTien', 'LoiNhuan']].sum().reset_index()
            
            # Chuyển sang triệu đồng
            daily_stats['DoanhThuTrieu'] = daily_stats['ThanhTien'] / 1_000_000
            daily_stats['LoiNhuanTrieu'] = daily_stats['LoiNhuan'] / 1_000_000
            
            fig_month = go.Figure()
            fig_month.add_trace(go.Bar(x=daily_stats['Ngay'], y=daily_stats['DoanhThuTrieu'], name="Doanh thu (Cột)", marker_color='#1f77b4'))
            fig_month.add_trace(go.Scatter(x=daily_stats['Ngay'], y=daily_stats['LoiNhuanTrieu'], name="Lợi nhuận (Đường)", yaxis="y2", line=dict(color='#d62728', width=3), mode='lines+markers'))
            
            fig_month.update_layout(
                hovermode="x unified",
                yaxis=dict(title="Doanh thu (Triệu VNĐ)", side="left"),
                yaxis2=dict(title="Lợi nhuận (Triệu VNĐ)", side="right", overlaying="y", showgrid=False),
                legend=dict(x=0, y=1.1, orientation="h"),
                margin=dict(l=20, r=20, t=50, b=20),
                height=450
            )
            st.plotly_chart(fig_month, use_container_width=True)
        else:
            st.warning("Chưa có dữ liệu bán hàng trong tháng này.")

        st.divider()

        # 2. Báo cáo Năm Hiện Tại (Theo từng tháng)
        st.subheader(f"2. Hiệu quả kinh doanh Năm {today.year}")
        df_year = df_sales[df_sales['NgayBan'].dt.year == today.year].copy()
        
        if not df_year.empty:
            df_year['Thang'] = df_year['NgayBan'].dt.strftime('Tháng %m')
            # Đảm bảo sắp xếp đúng thứ tự tháng
            monthly_stats = df_year.groupby('Thang')[['ThanhTien', 'LoiNhuan']].sum().reset_index()
            
            monthly_stats['DoanhThuTrieu'] = monthly_stats['ThanhTien'] / 1_000_000
            monthly_stats['LoiNhuanTrieu'] = monthly_stats['LoiNhuan'] / 1_000_000
            
            fig_year = go.Figure()
            fig_year.add_trace(go.Bar(x=monthly_stats['Thang'], y=monthly_stats['DoanhThuTrieu'], name="Doanh thu (Cột)", marker_color='#2ca02c'))
            fig_year.add_trace(go.Scatter(x=monthly_stats['Thang'], y=monthly_stats['LoiNhuanTrieu'], name="Lợi nhuận (Đường)", yaxis="y2", line=dict(color='#ff7f0e', width=3), mode='lines+markers'))
            
            fig_year.update_layout(
                hovermode="x unified",
                yaxis=dict(title="Doanh thu (Triệu VNĐ)", side="left"),
                yaxis2=dict(title="Lợi nhuận (Triệu VNĐ)", side="right", overlaying="y", showgrid=False),
                legend=dict(x=0, y=1.1, orientation="h"),
                margin=dict(l=20, r=20, t=50, b=20),
                height=450
            )
            st.plotly_chart(fig_year, use_container_width=True)
        else:
            st.warning("Chưa có dữ liệu bán hàng trong năm này.")
# --- MAIN APP ---
def main():
    # Kiem tra dang nhap
    if not st.session_state['is_logged_in']:
        render_login()
    else:
        # Load data 1 lan
        df_inventory = dm.load_inventory()
        
        # Sidebar Menu
        with st.sidebar:
            st.title("Admin Panel")
            menu = st.radio("Chức năng", ["Bán Hàng", "Nhập Hàng", "Báo Cáo"], index=0)
            st.divider()
            if st.button("Đăng Xuất"):
                st.session_state['is_logged_in'] = False
                st.rerun()
        
        # Routing
        if menu == "Bán Hàng":
            render_sales(df_inventory)
        elif menu == "Nhập Hàng":
            render_import(df_inventory)
        elif menu == "Báo Cáo":
            render_reports(df_inventory)

if __name__ == "__main__":
    main()