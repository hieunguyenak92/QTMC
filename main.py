import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import data_manager as dm

# --- 1. CẤU HÌNH GIAO DIỆN CHUYÊN NGHIỆP ---
st.set_page_config(
    page_title="Minh Châu Pharmacy POS", 
    layout="wide", 
    page_icon="💊"
)

st.markdown("""
<style>
    .stButton>button {width: 100%; border-radius: 8px; height: 3em; font-weight: 600;}
    div[data-testid="stMetricValue"] {font-size: 1.4rem; color: #0068C9; font-weight: 700;}
    .header-title {font-size: 2.2em; font-weight: 800; color: #154360; margin: 0;}
    .header-subtitle {font-size: 1.1em; color: #555; font-style: italic;}
    .success-box {padding: 1rem; background-color: #d4edda; border-radius: 5px; color: #155724;}
    .warning-box {padding: 1rem; background-color: #fff3cd; border-radius: 5px; color: #856404;}
</style>
""", unsafe_allow_html=True)

# --- QUẢN LÝ TRẠNG THÁI ---
if 'is_logged_in' not in st.session_state: st.session_state['is_logged_in'] = False
if 'sales_cart' not in st.session_state: st.session_state['sales_cart'] = []
if 'import_cart' not in st.session_state: st.session_state['import_cart'] = []

# --- HÀM HỖ TRỢ ---
def format_currency(amount):
    return f"{amount:,.0f} đ"

def render_header():
    c1, c2 = st.columns([1, 8])
    with c1:
        st.write("🏥") # Có thể thay bằng st.image nếu có logo
    with c2:
        st.markdown('<p class="header-title">Quầy Thuốc Minh Châu 24h</p>', unsafe_allow_html=True)
        st.markdown('<p class="header-subtitle">Hệ thống quản lý dược phẩm chuyên nghiệp</p>', unsafe_allow_html=True)
    st.divider()

# --- CÁC MÀN HÌNH CHỨC NĂNG ---

def render_login():
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.info("👋 Chào mừng trở lại!")
        with st.form("login_form"):
            password = st.text_input("Mật khẩu hệ thống", type="password")
            submitted = st.form_submit_button("Đăng Nhập")
            if submitted:
                sys_pass = st.secrets.get("app_password", "123456")
                if password == sys_pass:
                    st.session_state['is_logged_in'] = True
                    st.rerun()
                else:
                    st.error("Sai mật khẩu!")

def render_sales(df_inv):
    st.subheader("🛒 Bán Hàng & Thu Ngân")
    col_search, col_cart = st.columns([6, 4], gap="large")
    
    with col_search:
        st.caption("Tra cứu và chọn sản phẩm")
        if not df_inv.empty:
            df_inv['display'] = df_inv.apply(lambda x: f"{x['TenSanPham']} - {format_currency(x['GiaBan'])}/ {x['DonVi']} (Kho: {x['SoLuong']})", axis=1)
            options = [""] + df_inv['display'].tolist()
            selected = st.selectbox("🔍 Tìm thuốc (Tên/Mã):", options=options)
            
            if selected:
                item = df_inv[df_inv['display'] == selected].iloc[0]
                with st.container(border=True):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.markdown(f"### {item['TenSanPham']}")
                        st.write(f"**Mã:** {item['MaSanPham']} | **Đơn vị:** {item['DonVi']}")
                        st.write(f"**Tồn kho:** {item['SoLuong']}")
                    with c2:
                        st.metric("Giá bán", format_currency(item['GiaBan']))
                        qty = st.number_input("Số lượng:", min_value=1, value=1)
                    
                    if st.button("Thêm vào đơn", type="primary"):
                        if qty > item['SoLuong']:
                            st.error(f"⚠️ Kho chỉ còn {item['SoLuong']} {item['DonVi']}")
                        else:
                            st.session_state['sales_cart'].append({
                                "MaSanPham": item['MaSanPham'], "TenSanPham": item['TenSanPham'],
                                "DonVi": item['DonVi'], "GiaBan": float(item['GiaBan']),
                                "SoLuongBan": qty, "ThanhTien": qty * item['GiaBan']
                            })
                            st.toast("Đã thêm vào giỏ!", icon="✅")
                            
    with col_cart:
        st.caption("Chi tiết đơn hàng")
        with st.container(border=True):
            if st.session_state['sales_cart']:
                df_cart = pd.DataFrame(st.session_state['sales_cart'])
                st.dataframe(df_cart[['TenSanPham', 'SoLuongBan', 'ThanhTien']], use_container_width=True, hide_index=True)
                
                total = df_cart['ThanhTien'].sum()
                st.divider()
                st.markdown(f"<h3 style='text-align: right; color: #E74C3C;'>Tổng: {format_currency(total)}</h3>", unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                if c1.button("Hủy đơn"):
                    st.session_state['sales_cart'] = []
                    st.rerun()
                if c2.button("Thanh Toán", type="primary"):
                    if dm.process_checkout(st.session_state['sales_cart']):
                        st.session_state['sales_cart'] = []
                        st.balloons()
                        st.success("Giao dịch thành công!")
                        st.rerun()
            else:
                st.info("Chưa có sản phẩm nào.")

def render_import(df_inv):
    st.subheader("📦 Quản Lý Kho & Nhập Hàng")
    tab1, tab2 = st.tabs(["Nhập Hàng Có Sẵn", "Khai Báo Thuốc Mới"])
    
    with tab1:
        if not df_inv.empty:
            sel = st.selectbox("Chọn thuốc:", [""] + df_inv['TenSanPham'].tolist())
            if sel:
                item = df_inv[df_inv['TenSanPham'] == sel].iloc[0]
                with st.form("import_old"):
                    c1, c2, c3 = st.columns(3)
                    new_q = c1.number_input("Số lượng nhập", 1, 100)
                    new_in = c2.number_input("Giá nhập mới", 0.0, float(item['GiaNhap']))
                    new_out = c3.number_input("Giá bán mới", 0.0, float(item['GiaBan']))
                    
                    if st.form_submit_button("Thêm vào phiếu nhập"):
                        st.session_state['import_cart'].append({
                            "MaSanPham": item['MaSanPham'], "TenSanPham": item['TenSanPham'],
                            "DonVi": item['DonVi'], "SoLuong": new_q, 
                            "GiaNhap": new_in, "GiaBan": new_out, "NhaCungCap": item.get("NhaCungCap", "")
                        })
                        st.rerun()
    
    with tab2:
        with st.form("import_new"):
            st.write("Khai báo thông tin thuốc mới")
            c1, c2 = st.columns([1,3])
            new_id = c1.text_input("Mã Thuốc (duy nhất)", value=f"SP{len(df_inv)+1}")
            new_name = c2.text_input("Tên Biệt Dược")
            c3, c4, c5 = st.columns(3)
            new_unit = c3.selectbox("Đơn vị", ["Viên", "Vỉ", "Hộp", "Chai", "Tuýp", "Gói"])
            new_prov = c4.text_input("Nhà cung cấp")
            new_qty = c5.number_input("Số lượng đầu kỳ", 1, 10)
            c6, c7 = st.columns(2)
            p_in = c6.number_input("Giá Nhập", 0.0, step=1000.0)
            p_out = c7.number_input("Giá Bán", 0.0, step=1000.0)
            
            if st.form_submit_button("Lưu thuốc mới"):
                if new_name:
                    st.session_state['import_cart'].append({
                        "MaSanPham": new_id, "TenSanPham": new_name, "DonVi": new_unit,
                        "SoLuong": new_qty, "GiaNhap": p_in, "GiaBan": p_out, "NhaCungCap": new_prov
                    })
                    st.rerun()

    if st.session_state['import_cart']:
        st.write("---")
        st.write("### 📝 Phiếu Nhập Kho Tạm Tính")
        st.dataframe(pd.DataFrame(st.session_state['import_cart']))
        if st.button("Xác nhận nhập kho", type="primary"):
            if dm.process_import(st.session_state['import_cart']):
                st.session_state['import_cart'] = []
                st.success("Cập nhật kho thành công!")
                st.rerun()

# --- PHẦN 4: BÁO CÁO (ĐÃ NÂNG CẤP & SỬA LỖI) ---
# --- HÀM BÁO CÁO (ĐÃ FIX TRỤC HOÀNH TRIỆT ĐỂ) ---
def render_reports(df_inv):
    st.subheader("📊 Trung Tâm Báo Cáo & Phân Tích")
    
    # Load dữ liệu
    df_sales = dm.load_sales_history()
    df_expenses = dm.load_expenses() 
    
    tabs = st.tabs(["💵 Sổ Quỹ & Lãi Ròng", "📅 Doanh Thu Tháng", "📈 Hiệu Quả Năm", "📦 Tồn Kho"])
    
    # --- TAB 1: SỔ QUỸ (Giữ nguyên logic cũ) ---
    with tabs[0]:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.info("💡 Nhập chi phí vận hành (Điện, nước, lương...) để tính lãi thực.")
            with st.form("add_expense"):
                ex_date = st.date_input("Ngày chi", datetime.now())
                ex_type = st.selectbox("Loại", ["Chi phí vận hành", "Lương nhân viên", "Thuê mặt bằng", "Khác"])
                ex_amount = st.number_input("Số tiền (VND)", min_value=0.0, step=10000.0)
                ex_reason = st.text_input("Diễn giải")
                if st.form_submit_button("Ghi sổ"):
                    if dm.add_expense(ex_date, ex_type, ex_amount, ex_reason):
                        st.success("Đã ghi sổ!")
                        st.rerun()
        
        with c2:
            st.write("### 💰 Báo Cáo Lợi Nhuận Thực Tế (Tháng này)")
            this_month = datetime.now().month
            this_year = datetime.now().year
            
            revenue = 0
            cogs = 0
            expenses = 0
            
            if not df_sales.empty:
                # Chuyển đổi sang datetime nếu chưa phải
                if not pd.api.types.is_datetime64_any_dtype(df_sales['NgayBan']):
                    df_sales['NgayBan'] = pd.to_datetime(df_sales['NgayBan'])
                
                df_s_month = df_sales[(df_sales['NgayBan'].dt.month == this_month) & (df_sales['NgayBan'].dt.year == this_year)]
                revenue = df_s_month['ThanhTien'].sum()
                cogs = df_s_month['GiaVonLucBan'].sum() if 'GiaVonLucBan' in df_s_month.columns else 0
            
            if not df_expenses.empty:
                if not pd.api.types.is_datetime64_any_dtype(df_expenses['Ngay']):
                    df_expenses['Ngay'] = pd.to_datetime(df_expenses['Ngay'])
                df_e_month = df_expenses[(df_expenses['Ngay'].dt.month == this_month)]
                expenses = df_e_month['SoTien'].sum()
                
            gross_profit = revenue - cogs
            net_profit = gross_profit - expenses
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Doanh Thu", f"{revenue:,.0f}")
            m2.metric("Lợi Nhuận Gộp", f"{gross_profit:,.0f}", delta=f"{(gross_profit/revenue)*100:.1f}%" if revenue else "0%")
            m3.metric("Chi Phí", f"-{expenses:,.0f}")
            m4.metric("LÃI RÒNG", f"{net_profit:,.0f}", delta_color="normal")

    # --- TAB 2: BIỂU ĐỒ NGÀY (FIXED: KHÔNG CÒN SỐ ÂM) ---
    with tabs[1]:
        st.write(f"### 🗓 Diễn biến kinh doanh Tháng {datetime.now().month}")
        
        # 1. Tạo khung dữ liệu chuẩn từ ngày 1 đến 31 (Bắt buộc có đủ 31 ngày)
        # Sử dụng hàm calendar để lấy số ngày chính xác của tháng hiện tại thì tốt hơn, nhưng để an toàn cứ lấy 31
        days_range = list(range(1, 32)) 
        chart_data = pd.DataFrame({'Day': days_range})
        chart_data['ThanhTien'] = 0.0
        chart_data['LoiNhuan'] = 0.0

        if not df_sales.empty:
            df_month = df_sales[(df_sales['NgayBan'].dt.month == datetime.now().month) & (df_sales['NgayBan'].dt.year == datetime.now().year)]
            if not df_month.empty:
                daily_data = df_month.groupby(df_month['NgayBan'].dt.day)[['ThanhTien', 'LoiNhuan']].sum()
                # Map dữ liệu vào khung chuẩn
                for day_idx in daily_data.index:
                    chart_data.loc[chart_data['Day'] == day_idx, 'ThanhTien'] = daily_data.loc[day_idx, 'ThanhTien']
                    chart_data.loc[chart_data['Day'] == day_idx, 'LoiNhuan'] = daily_data.loc[day_idx, 'LoiNhuan']

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=chart_data['Day'], y=chart_data['ThanhTien'], 
            name="Doanh Thu", marker_color='#2E86C1'
        ))
        fig.add_trace(go.Scatter(
            x=chart_data['Day'], y=chart_data['LoiNhuan'], 
            name="Lợi Nhuận", line=dict(color='#E74C3C', width=3), mode='lines+markers'
        ))
        
        # --- FIX QUAN TRỌNG NHẤT Ở ĐÂY ---
        fig.update_layout(
            xaxis=dict(
                tickmode='array',          # Chế độ mảng cố định
                tickvals=days_range,       # Chỉ hiển thị các số: 1, 2, ..., 31
                range=[0.5, 31.5],         # Khóa cứng khung nhìn
                title="Ngày trong tháng",
                fixedrange=True            # Không cho user zoom làm lệch trục
            ),
            yaxis=dict(title="Số tiền (VNĐ)"),
            legend=dict(orientation="h", y=1.1),
            height=450,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- TAB 3: BIỂU ĐỒ NĂM (FIXED: KHÔNG CÒN SỐ ÂM) ---
    with tabs[2]:
        st.write(f"### 📅 Tổng kết năm {datetime.now().year}")
        
        # 1. Tạo khung dữ liệu chuẩn 12 tháng
        months_range = list(range(1, 13))
        chart_year = pd.DataFrame({'Month': months_range})
        chart_year['ThanhTien'] = 0.0
        chart_year['LoiNhuan'] = 0.0
        
        if not df_sales.empty:
            current_year = datetime.now().year
            df_year = df_sales[df_sales['NgayBan'].dt.year == current_year]
            if not df_year.empty:
                monthly_data = df_year.groupby(df_year['NgayBan'].dt.month)[['ThanhTien', 'LoiNhuan']].sum()
                for m_idx in monthly_data.index:
                    chart_year.loc[chart_year['Month'] == m_idx, 'ThanhTien'] = monthly_data.loc[m_idx, 'ThanhTien']
                    chart_year.loc[chart_year['Month'] == m_idx, 'LoiNhuan'] = monthly_data.loc[m_idx, 'LoiNhuan']
        
        fig_y = go.Figure()
        fig_y.add_trace(go.Bar(
            x=chart_year['Month'], y=chart_year['ThanhTien'], 
            name="Doanh Thu", marker_color='#117A65'
        ))
        fig_y.add_trace(go.Scatter(
            x=chart_year['Month'], y=chart_year['LoiNhuan'], 
            name="Lợi Nhuận", line=dict(color='#F39C12', width=3), yaxis="y2"
        ))
        
        # --- FIX QUAN TRỌNG NHẤT Ở ĐÂY ---
        fig_y.update_layout(
            xaxis=dict(
                tickmode='array',           # Chế độ mảng cố định
                tickvals=months_range,      # Chỉ hiện số 1 đến 12
                ticktext=[f"T{i}" for i in months_range], # Hiển thị T1, T2... cho gọn
                range=[0.5, 12.5],          # Khóa cứng khung nhìn
                title="Tháng",
                fixedrange=True
            ),
            yaxis=dict(title="Doanh thu"),
            yaxis2=dict(title="Lợi nhuận", overlaying="y", side="right", showgrid=False),
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig_y, use_container_width=True)

    with tabs[3]:
        st.write("### 📦 Giá Trị Kho Hàng")
        if not df_inv.empty:
            if 'SoLuong' in df_inv.columns and 'GiaNhap' in df_inv.columns:
                total_val = (pd.to_numeric(df_inv['SoLuong']) * pd.to_numeric(df_inv['GiaNhap'])).sum()
                st.metric("Tổng vốn tồn kho", f"{total_val:,.0f} đ")
            st.dataframe(df_inv, use_container_width=True)

def main():
    if not st.session_state['is_logged_in']:
        render_login()
    else:
        render_header()
        df_inv = dm.load_inventory()
        
        # Menu kiểu tab ngang hiện đại hơn sidebar
        menu = st.radio("", ["Bán Hàng", "Nhập Hàng", "Báo Cáo"], horizontal=True, label_visibility="collapsed")
        st.divider()
        
        if menu == "Bán Hàng": render_sales(df_inv)
        elif menu == "Nhập Hàng": render_import(df_inv)
        elif menu == "Báo Cáo": render_reports(df_inv)

if __name__ == "__main__":
    main()
