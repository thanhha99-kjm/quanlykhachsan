import datetime
import os
import sqlite3
import pandas as pd
import streamlit as st

# ==========================================
# CẤU HÌNH TRANG VÀ KẾT NỐI DATABASE
# ==========================================
st.set_page_config(
    page_title="dmelin hotel - Hệ thống Quản lý Khách sạn",
    page_icon="🏨",
    layout="wide"
)

IMAGE_PATH = "images (1).jpg"

@st.cache_resource
def get_connection():
    return sqlite3.connect("hotel.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Bảng danh sách phòng
    c.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            room_number TEXT PRIMARY KEY,
            room_type TEXT,
            price_per_night REAL,
            status TEXT DEFAULT 'Trống'
        )
    ''')
    
    # Bảng đặt phòng / lưu trú
    c.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT,
            customer_name TEXT,
            customer_id TEXT,
            phone_number TEXT,
            email TEXT,
            nationality TEXT,
            notes TEXT,
            check_in_date TEXT,
            check_out_date TEXT,
            status TEXT DEFAULT 'Đang ở',
            total_room_cost REAL DEFAULT 0,
            service_cost REAL DEFAULT 0,
            total_amount REAL DEFAULT 0
        )
    ''')
    
    # Bảng dịch vụ sử dụng
    c.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER,
            service_name TEXT,
            price REAL,
            quantity INTEGER,
            total REAL
        )
    ''')
    conn.commit()

    # 1. Khởi tạo danh sách phòng
    c.execute("SELECT COUNT(*) FROM rooms")
    if c.fetchone()[0] == 0:
        sample_rooms = [
            ('101', 'Đơn Standard', 500000, 'Trống'),
            ('102', 'Đơn Standard', 500000, 'Đã đặt'),  # Phòng đang có khách
            ('201', 'Đôi Deluxe', 800000, 'Trống'),
            ('202', 'Đôi Deluxe', 800000, 'Đã đặt'),   # Phòng đang có khách
            ('301', 'VIP Suite', 1500000, 'Trống'),
        ]
        c.executemany("INSERT INTO rooms VALUES (?, ?, ?, ?)", sample_rooms)
        conn.commit()

    # 2. Khởi tạo dữ liệu ĐÃ Ở (3 lượt) và ĐANG Ở (2 lượt)
    c.execute("SELECT COUNT(*) FROM bookings")
    if c.fetchone()[0] == 0:
        sample_bookings = [
            # --- 3 PHÒNG ĐÃ Ở & CHECK-OUT HOÀN TẤT ---
            ('101', 'Nguyễn Văn An', '079201001234', '0903123456', 'an.nguyen@gmail.com', 'Việt Nam', 'Yêu cầu phòng yên tĩnh', '2026-09-20', '2026-09-22', 'Đã trả phòng', 1000000, 30000, 1030000),
            ('201', 'Trần Thị Bích', '079198005678', '0918987654', 'bich.tran@yahoo.com', 'Việt Nam', 'Khách VIP đi công tác', '2026-09-23', '2026-09-26', 'Đã trả phòng', 2400000, 150000, 2550000),
            ('301', 'Michael Smith', 'C987654321', '0933112233', 'm.smith@outlook.com', 'Mỹ', 'Khách hàng thân thiết', '2026-09-26', '2026-09-28', 'Đã trả phòng', 3000000, 200000, 3200000),
            
            # --- 2 PHÒNG ĐANG Ở / ĐÃ ĐẶT (Đang lưu trú tại khách sạn) ---
            ('102', 'Lê Hoàng Nam', '079195009988', '0977889900', 'nam.le@gmail.com', 'Việt Nam', 'Gọi báo thức 7h sáng', '2026-09-28', '2026-09-30', 'Đang ở', 0, 0, 0),
            ('202', 'Phạm Minh Khoa', '079192003344', '0966554433', 'khoa.pham@gmail.com', 'Việt Nam', 'Thêm 1 bộ khăn tắm', '2026-09-27', '2026-09-30', 'Đang ở', 0, 0, 0)
        ]
        c.executemany('''
            INSERT INTO bookings (
                room_number, customer_name, customer_id, phone_number, email,
                nationality, notes, check_in_date, check_out_date, status,
                total_room_cost, service_cost, total_amount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_bookings)
        
        # Thêm dịch vụ cho các phòng
        sample_services = [
            (1, 'Nước suối', 15000, 2, 30000),
            (2, 'Cà phê', 30000, 3, 90000),
            (2, 'Giặt ủi', 60000, 1, 60000),
            (3, 'Nước ép hoa quả', 50000, 4, 200000),
            (4, 'Nước suối', 15000, 2, 30000),  # Dịch vụ phòng 102 đang ở
            (5, 'Mì ly', 20000, 2, 40000)      # Dịch vụ phòng 202 đang ở
        ]
        c.executemany("INSERT INTO services (booking_id, service_name, price, quantity, total) VALUES (?, ?, ?, ?, ?)", sample_services)
        conn.commit()

init_db()
conn = get_connection()

# ==========================================
# THANH ĐIỀU HƯỚNG (SIDEBAR)
# ==========================================
if os.path.exists(IMAGE_PATH):
    st.sidebar.image(IMAGE_PATH)
else:
    st.sidebar.warning(f"⚠️ Chưa thấy file '{IMAGE_PATH}' trong thư mục.")

st.sidebar.title("🏨 dmelin hotel")
menu = st.sidebar.radio(
    "Danh mục quản lý",
    [
        "Sơ đồ phòng", 
        "Check-in (Nhận phòng)", 
        "Dịch vụ & Check-out", 
        "Quản lý khách lưu trú", 
        "Thống kê doanh thu", 
        "Cấu hình phòng"
    ]
)

# ==========================================
# 1. SƠ ĐỒ PHÒNG
# ==========================================
if menu == "Sơ đồ phòng":
    st.title("📌 Sơ đồ & Trạng thái phòng - dmelin hotel")
    
    if os.path.exists(IMAGE_PATH):
        col_img, col_info = st.columns([1, 2])
        with col_img:
            st.image(IMAGE_PATH, caption="dmelin hotel")
        with col_info:
            st.subheader("Chào mừng đến với Hệ thống Quản lý Khách sạn dmelin hotel")
            st.caption("Theo dõi tình trạng phòng, lượt lưu trú và dịch vụ thời gian thực.")
    
    rooms_df = pd.read_sql_query("SELECT * FROM rooms", conn)
    
    col_a, col_b, col_c = st.columns(3)
    total_r = len(rooms_df)
    occupied_r = len(rooms_df[rooms_df['status'] == 'Đã đặt'])
    available_r = total_r - occupied_r
    
    col_a.metric("Tổng số phòng", total_r)
    col_b.metric("Phòng đang có khách", occupied_r)
    col_c.metric("Phòng trống", available_r)
    
    st.markdown("---")
    
    cols = st.columns(3)
    for index, row in rooms_df.iterrows():
        col = cols[index % 3]
        with col:
            status_color = "🔴" if row['status'] == 'Đã đặt' else "🟢"
            with st.container(border=True):
                st.subheader(f"Phòng {row['room_number']} {status_color}")
                st.write(f"**Loại:** {row['room_type']}")
                st.write(f"**Giá:** {row['price_per_night']:,} VNĐ/đêm")
                st.write(f"**Trạng thái:** {row['status']}")
                
                if row['status'] == 'Đã đặt':
                    b_df = pd.read_sql_query(
                        "SELECT customer_name, phone_number, check_in_date FROM bookings WHERE room_number = ? AND status = 'Đang ở'",
                        conn, params=(row['room_number'],)
                    )
                    if not b_df.empty:
                        st.caption(f"👤 Khách: {b_df.iloc[0]['customer_name']}")
                        st.caption(f"📞 SĐT: {b_df.iloc[0]['phone_number']}")
                        st.caption(f"📅 Nhận: {b_df.iloc[0]['check_in_date']}")

# ==========================================
# 2. CHECK-IN (NHẬN PHÒNG)
# ==========================================
elif menu == "Check-in (Nhận phòng)":
    st.title("🔑 Lập phiếu nhận phòng - dmelin hotel")
    
    available_rooms_df = pd.read_sql_query("SELECT room_number, room_type, price_per_night FROM rooms WHERE status = 'Trống'", conn)
    
    if available_rooms_df.empty:
        st.warning("Hiện tại không còn phòng trống!")
    else:
        room_options = [f"{row['room_number']} - {row['room_type']} ({row['price_per_night']:,} VNĐ)" for _, row in available_rooms_df.iterrows()]
        
        with st.form("checkin_form"):
            st.subheader("1. Chọn phòng & Thời gian")
            selected_room_str = st.selectbox("Chọn phòng trống", room_options)
            
            col1, col2 = st.columns(2)
            check_in_date = col1.date_input("Ngày nhận phòng", datetime.date.today())
            check_out_date = col2.date_input("Ngày dự kiến trả phòng", datetime.date.today() + datetime.timedelta(days=1))
            
            st.subheader("2. Thông tin khách lưu trú")
            c_col1, c_col2 = st.columns(2)
            customer_name = c_col1.text_input("Họ và tên khách hàng *")
            customer_id = c_col2.text_input("Số CCCD / Hộ chiếu *")
            
            p_col1, p_col2, p_col3 = st.columns(3)
            phone_number = p_col1.text_input("Số điện thoại")
            email = p_col2.text_input("Email")
            nationality = p_col3.text_input("Quốc tịch", value="Việt Nam")
            
            notes = st.text_area("Ghi chú đặc biệt (Ví dụ: Yêu cầu phòng tầng cao, thêm gối...)")
            
            submit = st.form_submit_button("Thực hiện Check-in")
            
            if submit:
                if not customer_name or not customer_id:
                    st.error("Vui lòng điền các thông tin bắt buộc (*)")
                elif check_out_date <= check_in_date:
                    st.error("Ngày trả phòng phải sau ngày nhận phòng!")
                else:
                    room_num = selected_room_str.split(" - ")[0]
                    c = conn.cursor()
                    
                    c.execute('''
                        INSERT INTO bookings (
                            room_number, customer_name, customer_id, phone_number, email, 
                            nationality, notes, check_in_date, check_out_date, status
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Đang ở')
                    ''', (
                        room_num, customer_name, customer_id, phone_number, email, 
                        nationality, notes, str(check_in_date), str(check_out_date)
                    ))
                    
                    c.execute("UPDATE rooms SET status = 'Đã đặt' WHERE room_number = ?", (room_num,))
                    
                    conn.commit()
                    st.success(f"Check-in thành công cho phòng {room_num} tại dmelin hotel!")
                    st.rerun()

# ==========================================
# 3. DỊCH VỤ & CHECK-OUT (TRẢ PHÒNG)
# ==========================================
elif menu == "Dịch vụ & Check-out":
    st.title("🛠️ Dịch vụ phát sinh & Thanh toán")
    
    active_bookings = pd.read_sql_query('''
        SELECT id, room_number, customer_name, check_in_date 
        FROM bookings 
        WHERE status = 'Đang ở'
    ''', conn)
    
    if active_bookings.empty:
        st.info("Hiện không có phòng nào đang có khách lưu trú.")
    else:
        booking_dict = {
            f"Phòng {row['room_number']} - Khách: {row['customer_name']} (Mã phiếu: {row['id']})": row['id']
            for _, row in active_bookings.iterrows()
        }
        
        selected_label = st.selectbox("Chọn lượt lưu trú cần xử lý", list(booking_dict.keys()))
        selected_booking_id = booking_dict[selected_label]
        
        tab1, tab2 = st.tabs(["➕ Thêm dịch vụ", "💳 Thanh toán & Check-out"])
        
        with tab1:
            st.subheader("Ghi nhận dịch vụ / Nước uống phát sinh")
            with st.form("service_form"):
                srv_name = st.text_input("Tên dịch vụ / Mặt hàng", value="Nước suối")
                srv_price = st.number_input("Đơn giá (VNĐ)", min_value=0, value=15000, step=5000)
                srv_qty = st.number_input("Số lượng", min_value=1, value=1, step=1)
                
                srv_submit = st.form_submit_button("Thêm vào hóa đơn")
                if srv_submit:
                    total_srv = srv_price * srv_qty
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO services (booking_id, service_name, price, quantity, total)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (selected_booking_id, srv_name, srv_price, srv_qty, total_srv))
                    conn.commit()
                    st.success(f"Đã thêm {srv_qty}x {srv_name} vào hóa đơn.")
            
            srv_list = pd.read_sql_query("SELECT service_name as 'Tên dịch vụ', price as 'Đơn giá', quantity as 'Số lượng', total as 'Thành tiền' FROM services WHERE booking_id = ?", conn, params=(selected_booking_id,))
            if not srv_list.empty:
                st.write("**Dịch vụ đã sử dụng:**")
                st.dataframe(srv_list)
        
        with tab2:
            st.subheader("Chi tiết hóa đơn & Trả phòng")
            
            b_info = pd.read_sql_query('''
                SELECT b.*, r.price_per_night 
                FROM bookings b 
                JOIN rooms r ON b.room_number = r.room_number 
                WHERE b.id = ?
            ''', conn, params=(selected_booking_id,)).iloc[0]
            
            d_in = datetime.datetime.strptime(b_info['check_in_date'], "%Y-%m-%d").date()
            d_out = datetime.date.today()
            days = (d_out - d_in).days
            if days <= 0:
                days = 1
            
            room_cost = days * b_info['price_per_night']
            
            srv_tot_df = pd.read_sql_query("SELECT SUM(total) as srv_total FROM services WHERE booking_id = ?", conn, params=(selected_booking_id,))
            srv_cost = srv_tot_df.iloc[0]['srv_total'] if srv_tot_df.iloc[0]['srv_total'] is not None else 0
            
            grand_total = room_cost + srv_cost
            
            st.write(f"**Khách hàng:** {b_info['customer_name']} | **CCCD:** {b_info['customer_id']} | **SĐT:** {b_info['phone_number']}")
            st.write(f"**Quốc tịch:** {b_info['nationality']} | **Email:** {b_info['email']}")
            st.write(f"**Phòng:** {b_info['room_number']} | **Ngày vào:** {b_info['check_in_date']} | **Ngày trả:** {d_out}")
            if b_info['notes']:
                st.info(f"📌 Ghi chú: {b_info['notes']}")
            st.markdown("---")
            st.write(f"**Số ngày ở:** {days} đêm x {b_info['price_per_night']:,} VNĐ = **{room_cost:,} VNĐ**")
            st.write(f"**Tiền dịch vụ:** **{srv_cost:,} VNĐ**")
            st.markdown(f"### 💵 **Tổng thanh toán:** :red[{grand_total:,} VNĐ]")
            
            if st.button("Xác nhận thanh toán & Trả phòng", type="primary"):
                c = conn.cursor()
                c.execute('''
                    UPDATE bookings 
                    SET check_out_date = ?, status = 'Đã trả phòng', total_room_cost = ?, service_cost = ?, total_amount = ?
                    WHERE id = ?
                ''', (str(d_out), room_cost, srv_cost, grand_total, selected_booking_id))
                
                c.execute("UPDATE rooms SET status = 'Trống' WHERE room_number = ?", (b_info['room_number'],))
                
                conn.commit()
                st.balloons()
                st.success("Thanh toán hoàn tất! Phòng đã được đưa về trạng thái trống.")
                st.rerun()

# ==========================================
# 4. QUẢN LÝ KHÁCH LƯU TRÚ
# ==========================================
elif menu == "Quản lý khách lưu trú":
    st.title("📇 Hồ sơ khách lưu trú - dmelin hotel")
    
    search_keyword = st.text_input("🔍 Tìm kiếm theo Tên, CCCD hoặc Số điện thoại")
    
    query = '''
        SELECT 
            id as 'Mã Phiếu',
            customer_name as 'Họ tên',
            customer_id as 'CCCD/Hộ chiếu',
            phone_number as 'SĐT',
            email as 'Email',
            nationality as 'Quốc tịch',
            room_number as 'Phòng',
            check_in_date as 'Ngày vào',
            check_out_date as 'Ngày ra',
            total_amount as 'Doanh thu phát sinh (VNĐ)',
            status as 'Trạng thái'
        FROM bookings
    '''
    
    if search_keyword:
        query += f" WHERE customer_name LIKE '%{search_keyword}%' OR customer_id LIKE '%{search_keyword}%' OR phone_number LIKE '%{search_keyword}%'"
        
    query += " ORDER BY id DESC"
    
    guests_df = pd.read_sql_query(query, conn)
    
    if guests_df.empty:
        st.info("Chưa tìm thấy dữ liệu khách lưu trú phù hợp.")
    else:
        st.dataframe(guests_df)

# ==========================================
# 5. THỐNG KÊ DOANH THU & PHÒNG ĐANG Ở / ĐÃ Ở
# ==========================================
elif menu == "Thống kê doanh thu":
    st.title("📊 Thống kê doanh thu dmelin hotel")
    
    # 1. Doanh thu thực tế (đã trả phòng)
    history_df = pd.read_sql_query('''
        SELECT 
            b.id, b.room_number, r.room_type, b.customer_name, b.customer_id, b.phone_number,
            b.check_in_date, b.check_out_date, 
            b.total_room_cost, b.service_cost, b.total_amount, b.status 
        FROM bookings b
        JOIN rooms r ON b.room_number = r.room_number
        WHERE b.status = 'Đã trả phòng'
        ORDER BY b.check_out_date DESC
    ''', conn)
    
    # 2. Phòng đang có khách ở / đã đặt
    active_df = pd.read_sql_query('''
        SELECT 
            b.id, b.room_number, r.room_type, r.price_per_night, b.customer_name, b.customer_id, b.phone_number,
            b.check_in_date, b.check_out_date, b.status
        FROM bookings b
        JOIN rooms r ON b.room_number = r.room_number
        WHERE b.status = 'Đang ở'
    ''', conn)
    
    active_temp_revenue = 0
    if not active_df.empty:
        temp_rev_list = []
        for _, row in active_df.iterrows():
            d_in = datetime.datetime.strptime(row['check_in_date'], "%Y-%m-%d").date()
            d_today = datetime.date.today()
            days = (d_today - d_in).days
            if days <= 0:
                days = 1
            
            srv_tot_df = pd.read_sql_query("SELECT SUM(total) as srv_total FROM services WHERE booking_id = ?", conn, params=(row['id'],))
            srv_cost = srv_tot_df.iloc[0]['srv_total'] if srv_tot_df.iloc[0]['srv_total'] is not None else 0
            
            est_total = (days * row['price_per_night']) + srv_cost
            temp_rev_list.append(est_total)
            
        active_df['Tạm tính doanh thu (VNĐ)'] = temp_rev_list
        active_temp_revenue = sum(temp_rev_list)

    total_real_rev = history_df['total_amount'].sum() if not history_df.empty else 0
    total_room_rev = history_df['total_room_cost'].sum() if not history_df.empty else 0
    total_srv_rev = history_df['service_cost'].sum() if not history_df.empty else 0
    
    # Chỉ số tổng quan
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("THỰC THU (Đã check-out)", f"{total_real_rev:,} VNĐ")
    m2.metric("DỰ KIẾN (Khách đang ở)", f"{active_temp_revenue:,} VNĐ")
    m3.metric("Doanh thu tiền phòng", f"{total_room_rev:,} VNĐ")
    m4.metric("Doanh thu dịch vụ", f"{total_srv_rev:,} VNĐ")
    
    st.markdown("---")
    
    tab_active, tab_history, tab_vip = st.tabs([
        "🔴 Phòng đang ở / Đã đặt (2 phòng)", 
        "🟢 Phòng đã ở & Check-out (3 phòng)", 
        "👑 Doanh thu theo Khách hàng (VIP)"
    ])
    
    with tab_active:
        st.subheader("Danh sách các phòng đang có khách lưu trú")
        if active_df.empty:
            st.info("Hiện không có phòng nào đang có khách ở.")
        else:
            display_active = active_df[[
                'room_number', 'room_type', 'customer_name', 'phone_number', 
                'check_in_date', 'check_out_date', 'Tạm tính doanh thu (VNĐ)'
            ]]
            display_active.columns = ['Số phòng', 'Loại phòng', 'Khách hàng', 'SĐT', 'Ngày vào', 'Ngày ra dự kiến', 'Doanh thu tạm tính (VNĐ)']
            st.dataframe(display_active)
            
    with tab_history:
        st.subheader("Lịch sử các lượt phòng đã hoàn tất thanh toán")
        if history_df.empty:
            st.info("Chưa có lịch sử thanh toán.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Biểu đồ doanh thu thực tế theo ngày**")
                daily_rev = history_df.groupby('check_out_date')['total_amount'].sum().reset_index()
                daily_rev.columns = ['Ngày', 'Doanh thu']
                st.bar_chart(daily_rev.set_index('Ngày'))
            with c2:
                st.write("**Doanh thu thực tế theo loại phòng**")
                type_rev = history_df.groupby('room_type')['total_amount'].sum().reset_index()
                type_rev.columns = ['Loại phòng', 'Doanh thu']
                st.dataframe(type_rev)
                
            st.dataframe(history_df)

    with tab_vip:
        st.subheader("Tổng doanh thu đóng góp theo từng khách hàng (Đã trả phòng)")
        if history_df.empty:
            st.info("Chưa có dữ liệu giao dịch hoàn tất.")
        else:
            customer_rev = history_df.groupby(['customer_name', 'customer_id', 'phone_number']).agg(
                so_luot_o=('id', 'count'),
                tong_chi_tieu=('total_amount', 'sum'),
                tien_phong=('total_room_cost', 'sum'),
                tien_dich_vu=('service_cost', 'sum')
            ).reset_index().sort_values(by='tong_chi_tieu', ascending=False)
            
            customer_rev.columns = [
                'Họ và tên khách hàng', 
                'CCCD / Hộ chiếu', 
                'Số điện thoại', 
                'Số lượt lưu trú', 
                'Tổng doanh thu đóng góp (VNĐ)', 
                'Tiền phòng (VNĐ)', 
                'Tiền dịch vụ (VNĐ)'
            ]
            st.dataframe(customer_rev)

# ==========================================
# 6. CẤU HÌNH PHÒNG
# ==========================================
elif menu == "Cấu hình phòng":
    st.title("⚙️ Cấu hình danh mục phòng - dmelin hotel")
    
    with st.form("add_room_form"):
        st.subheader("Thêm phòng mới")
        new_room_num = st.text_input("Số phòng")
        new_room_type = st.selectbox("Loại phòng", ["Đơn Standard", "Đôi Deluxe", "VIP Suite", "Gia đình"])
        new_room_price = st.number_input("Giá phòng / đêm (VNĐ)", min_value=100000, value=500000, step=50000)
        
        add_submit = st.form_submit_button("Thêm phòng")
        if add_submit:
            if not new_room_num:
                st.error("Vui lòng nhập số phòng!")
            else:
                try:
                    c = conn.cursor()
                    c.execute("INSERT INTO rooms VALUES (?, ?, ?, 'Trống')", (new_room_num, new_room_type, new_room_price))
                    conn.commit()
                    st.success(f"Đã thêm phòng {new_room_num} thành công!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Số phòng này đã tồn tại!")

    st.markdown("---")
    st.subheader("Danh sách tất cả các phòng")
    all_rooms = pd.read_sql_query("SELECT room_number as 'Số phòng', room_type as 'Loại phòng', price_per_night as 'Giá/đêm (VNĐ)', status as 'Trạng thái' FROM rooms", conn)
    st.dataframe(all_rooms)
