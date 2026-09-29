import datetime
import sqlite3
import pandas as pd
import streamlit as st

# ==========================================
# CẤU HÌNH TRANG VÀ KẾT NỐI DATABASE
# ==========================================
st.set_page_config(
    page_title="Hệ thống Quản lý Khách sạn",
    page_icon="🏨",
    layout="wide"
)

# Quản lý kết nối DB an toàn trên Streamlit
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

    # Thêm dữ liệu phòng mẫu nếu bảng trống
    c.execute("SELECT COUNT(*) FROM rooms")
    if c.fetchone()[0] == 0:
        sample_rooms = [
            ('101', 'Đơn Standard', 500000, 'Trống'),
            ('102', 'Đơn Standard', 500000, 'Trống'),
            ('201', 'Đôi Deluxe', 800000, 'Trống'),
            ('202', 'Đôi Deluxe', 800000, 'Trống'),
            ('301', 'VIP Suite', 1500000, 'Trống'),
        ]
        c.executemany("INSERT INTO rooms VALUES (?, ?, ?, ?)", sample_rooms)
        conn.commit()

init_db()

# ==========================================
# THANH ĐIỀU HƯỚNG (SIDEBAR)
# ==========================================
st.sidebar.title("🏨 QL Khách Sạn")
menu = st.sidebar.radio(
    "Danh mục quản lý",
    ["Sơ đồ phòng", "Check-in (Nhận phòng)", "Dịch vụ & Check-out", "Thống kê & Quản lý phòng"]
)

conn = get_connection()

# ==========================================
# 1. SƠ ĐỒ PHÒNG
# ==========================================
if menu == "Sơ đồ phòng":
    st.title("📌 Sơ đồ & Trạng thái phòng")
    
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
                        "SELECT customer_name, check_in_date FROM bookings WHERE room_number = ? AND status = 'Đang ở'",
                        conn, params=(row['room_number'],)
                    )
                    if not b_df.empty:
                        st.caption(f"👤 Khách: {b_df.iloc[0]['customer_name']}")
                        st.caption(f"📅 Nhận: {b_df.iloc[0]['check_in_date']}")

# ==========================================
# 2. CHECK-IN (NHẬN PHÒNG)
# ==========================================
elif menu == "Check-in (Nhận phòng)":
    st.title("🔑 Lập phiếu nhận phòng")
    
    available_rooms_df = pd.read_sql_query("SELECT room_number, room_type, price_per_night FROM rooms WHERE status = 'Trống'", conn)
    
    if available_rooms_df.empty:
        st.warning("Hiện tại không còn phòng trống!")
    else:
        room_options = [f"{row['room_number']} - {row['room_type']} ({row['price_per_night']:,} VNĐ)" for _, row in available_rooms_df.iterrows()]
        
        with st.form("checkin_form"):
            selected_room_str = st.selectbox("Chọn phòng trống", room_options)
            customer_name = st.text_input("Họ và tên khách hàng")
            customer_id = st.text_input("Số CCCD / Hộ chiếu")
            
            col1, col2 = st.columns(2)
            check_in_date = col1.date_input("Ngày nhận phòng", datetime.date.today())
            check_out_date = col2.date_input("Ngày dự kiến trả phòng", datetime.date.today() + datetime.timedelta(days=1))
            
            submit = st.form_submit_button("Thực hiện Check-in")
            
            if submit:
                if not customer_name or not customer_id:
                    st.error("Vui lòng điền đầy đủ thông tin khách hàng!")
                elif check_out_date <= check_in_date:
                    st.error("Ngày trả phòng phải sau ngày nhận phòng!")
                else:
                    room_num = selected_room_str.split(" - ")[0]
                    c = conn.cursor()
                    
                    c.execute('''
                        INSERT INTO bookings (room_number, customer_name, customer_id, check_in_date, check_out_date, status)
                        VALUES (?, ?, ?, ?, ?, 'Đang ở')
                    ''', (room_num, customer_name, customer_id, str(check_in_date), str(check_out_date)))
                    
                    c.execute("UPDATE rooms SET status = 'Đã đặt' WHERE room_number = ?", (room_num,))
                    
                    conn.commit()
                    st.success(f"Check-in thành công cho phòng {room_num}!")
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
            st.subheader("Ghi nhận dịch vụ/nước uống")
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
            
            srv_list = pd.read_sql_query("SELECT service_name, price, quantity, total FROM services WHERE booking_id = ?", conn, params=(selected_booking_id,))
            if not srv_list.empty:
                st.write("**Dịch vụ đã sử dụng:**")
                st.dataframe(srv_list, use_container_width=True)
        
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
            
            st.write(f"**Khách hàng:** {b_info['customer_name']} (CCCD: {b_info['customer_id']})")
            st.write(f"**Phòng:** {b_info['room_number']} | **Ngày vào:** {b_info['check_in_date']} | **Ngày ra (Hôm nay):** {d_out}")
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
# 4. THỐNG KÊ & QUẢN LÝ PHÒNG
# ==========================================
elif menu == "Thống kê & Quản lý phòng":
    st.title("📊 Thống kê doanh thu & Cấu hình phòng")
    
    tab_stat, tab_manage = st.tabs(["📈 Báo cáo doanh thu", "⚙️ Quản lý danh mục phòng"])
    
    with tab_stat:
        st.subheader("Lịch sử thanh toán")
        history_df = pd.read_sql_query('''
            SELECT id, room_number, customer_name, check_in_date, check_out_date, total_room_cost, service_cost, total_amount 
            FROM bookings 
            WHERE status = 'Đã trả phòng'
            ORDER BY id DESC
        ''', conn)
        
        if history_df.empty:
            st.info("Chưa có dữ liệu thanh toán.")
        else:
            revenue = history_df['total_amount'].sum()
            st.metric("Tổng doanh thu tích lũy", f"{revenue:,} VNĐ")
            st.dataframe(history_df, use_container_width=True)
            
    with tab_manage:
        st.subheader("Thêm phòng mới")
        with st.form("add_room_form"):
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
        all_rooms = pd.read_sql_query("SELECT * FROM rooms", conn)
        st.dataframe(all_rooms, use_container_width=True)
