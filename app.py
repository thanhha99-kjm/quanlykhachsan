import datetime
import os
import pandas as pd
import psycopg2
from psycopg2 import extras
import streamlit as st
from PIL import Image

# ==========================================
# CẤU HÌNH TRANG & KẾT NỐI AIVEN POSTGRESQL
# ==========================================
st.set_page_config(
    page_title="dmelin hotel - Quản Lý Khách Sạn (Aiven DB)",
    page_icon="🏨",
    layout="wide"
)

IMAGE_FILE = "images (1).jpg"

def load_image_safe(image_path):
    """Đọc ảnh an toàn qua PIL"""
    if os.path.exists(image_path):
        try:
            return Image.open(image_path)
        except Exception:
            return None
    return None

# Lấy thông tin kết nối Aiven từ st.secrets hoặc thông số mặc định/thử nghiệm
def get_aiven_config():
    if "aiven" in st.secrets:
        return dict(st.secrets["aiven"])
    else:
        # Nếu chạy local mà chưa cấu hình secrets.toml, bạn có thể điền thông số Aiven ở đây
        return {
            "host": st.sidebar.text_input("Aiven Host", value="", type="password"),
            "port": st.sidebar.number_input("Aiven Port", value=22442),
            "dbname": st.sidebar.text_input("Aiven DB Name", value="defaultdb"),
            "user": st.sidebar.text_input("Aiven User", value="avnadmin"),
            "password": st.sidebar.text_input("Aiven Password", value="", type="password"),
            "sslmode": "require"
        }

@st.cache_resource(ttl=600)
def get_db_connection(config):
    try:
        conn = psycopg2.connect(**config)
        return conn
    except Exception as e:
        st.error(f"❌ Kết nối cơ sở dữ liệu Aiven thất bại: {e}")
        st.stop()

def init_db(conn):
    with conn.cursor() as c:
        # 1. Bảng phòng
        c.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                room_number VARCHAR(50) PRIMARY KEY,
                room_type VARCHAR(100),
                price_per_night NUMERIC,
                status VARCHAR(50) DEFAULT 'Trống'
            );
        ''')
        
        # 2. Bảng lưu trú / đặt phòng
        c.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                room_number VARCHAR(50),
                customer_name VARCHAR(150),
                customer_id VARCHAR(100),
                phone_number VARCHAR(50),
                email VARCHAR(100),
                nationality VARCHAR(100),
                notes TEXT,
                check_in_date DATE,
                check_out_date DATE,
                status VARCHAR(50) DEFAULT 'Đang ở',
                total_room_cost NUMERIC DEFAULT 0,
                service_cost NUMERIC DEFAULT 0,
                total_amount NUMERIC DEFAULT 0
            );
        ''')

        # 3. Bảng dịch vụ
        c.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id SERIAL PRIMARY KEY,
                booking_id INTEGER REFERENCES bookings(id) ON DELETE CASCADE,
                service_name VARCHAR(150),
                price NUMERIC,
                quantity INTEGER,
                total NUMERIC
            );
        ''')
        conn.commit()

        # Tạo dữ liệu phòng mẫu nếu chưa có
        c.execute("SELECT COUNT(*) FROM rooms;")
        if c.fetchone()[0] == 0:
            rooms_data = [
                ('101', 'Đơn Standard', 500000, 'Trống'),
                ('102', 'Đơn Standard', 500000, 'Trống'),
                ('201', 'Đôi Deluxe', 800000, 'Trống'),
                ('202', 'Đôi Deluxe', 800000, 'Trống'),
                ('301', 'VIP Suite', 1500000, 'Trống'),
            ]
            extras.execute_values(c, "INSERT INTO rooms (room_number, room_type, price_per_night, status) VALUES %s", rooms_data)
            conn.commit()

        # Tạo dữ liệu khách mẫu nếu chưa có
        c.execute("SELECT COUNT(*) FROM bookings;")
        if c.fetchone()[0] == 0:
            bookings_data = [
                ('101', 'Nguyễn Văn An', '079201001234', '0903123456', 'an.nguyen@gmail.com', 'Việt Nam', 'Phòng yên tĩnh', '2026-09-20', '2026-09-22', 'Đã trả phòng', 1000000, 30000, 1030000),
                ('201', 'Trần Thị Bích', '079198005678', '0918987654', 'bich.tran@yahoo.com', 'Việt Nam', 'Khách VIP', '2026-09-23', '2026-09-26', 'Đã trả phòng', 2400000, 150000, 2550000),
                ('301', 'Michael Smith', 'C987654321', '0933112233', 'm.smith@outlook.com', 'Mỹ', 'Khách quen', '2026-09-26', '2026-09-28', 'Đã trả phòng', 3000000, 200000, 3200000),
                ('102', 'Lê Hoàng Nam', '079195009988', '0977889900', 'nam.le@gmail.com', 'Việt Nam', 'Báo thức 7h', '2026-09-28', '2026-09-30', 'Đang ở', 0, 0, 0),
                ('202', 'Phạm Minh Khoa', '079192003344', '0966554433', 'khoa.pham@gmail.com', 'Việt Nam', 'Thêm khăn tắm', '2026-09-27', '2026-09-30', 'Đang ở', 0, 0, 0)
            ]
            extras.execute_values(c, '''
                INSERT INTO bookings (
                    room_number, customer_name, customer_id, phone_number, email,
                    nationality, notes, check_in_date, check_out_date, status,
                    total_room_cost, service_cost, total_amount
                ) VALUES %s
            ''', bookings_data)

            services_data = [
                (1, 'Nước suối', 15000, 2, 30000),
                (2, 'Cà phê', 30000, 3, 90000),
                (2, 'Giặt ủi', 60000, 1, 60000),
                (3, 'Nước ép hoa quả', 50000, 4, 200000),
                (4, 'Nước suối', 15000, 2, 30000),
                (5, 'Mì ly', 20000, 2, 40000)
            ]
            extras.execute_values(c, "INSERT INTO services (booking_id, service_name, price, quantity, total) VALUES %s", services_data)
            conn.commit()

        # ĐỒNG BỘ TRẠNG THÁI PHÒNG THEO DỮ LIỆU KHÁCH ĐANG Ở
        c.execute("UPDATE rooms SET status = 'Trống';")
        c.execute("UPDATE rooms SET status = 'Đã đặt' WHERE room_number IN (SELECT DISTINCT room_number FROM bookings WHERE status = 'Đang ở');")
        conn.commit()

# Khởi tạo thông số và kết nối Aiven
db_config = get_aiven_config()

if not db_config.get("host") or not db_config.get("password"):
    st.warning("⚠️ Vui lòng cấu hình thông tin kết nối Aiven trong thanh Sidebar hoặc qua `st.secrets` để tiếp tục.")
    st.stop()

conn = get_db_connection(db_config)
init_db(conn)

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
img_obj = load_image_safe(IMAGE_FILE)

if img_obj is not None:
    st.sidebar.image(img_obj)
else:
    st.sidebar.caption("🏨 dmelin hotel")

st.sidebar.title("Quản Lý Khách Sạn")
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
    st.title("📌 Sơ đồ & Trạng thái phòng - dmelin hotel (Aiven DB)")
    
    if img_obj is not None:
        c_img, c_txt = st.columns([1, 2])
        with c_img:
            st.image(img_obj)
        with c_txt:
            st.subheader("Chào mừng đến với dmelin hotel")
            st.write("Hệ thống quản lý phòng và doanh thu lưu trữ trên đám mây Aiven.")
    else:
        st.subheader("Chào mừng đến với dmelin hotel")
        st.write("Hệ thống quản lý phòng và doanh thu lưu trữ trên đám mây Aiven.")
    
    rooms_df = pd.read_sql_query("SELECT * FROM rooms ORDER BY room_number ASC", conn)
    
    total_r = len(rooms_df)
    occ_r = len(rooms_df[rooms_df['status'] == 'Đã đặt'])
    emp_r = total_r - occ_r
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng số phòng", total_r)
    col2.metric("Phòng đang có khách (Đã đặt)", occ_r)
    col3.metric("Phòng trống", emp_r)
    
    st.markdown("---")
    
    cols = st.columns(3)
    for idx, row in rooms_df.iterrows():
        with cols[idx % 3]:
            icon = "🔴" if row['status'] == 'Đã đặt' else "🟢"
            st.markdown(f"### Phòng {row['room_number']} {icon}")
            st.write(f"**Loại:** {row['room_type']}")
            st.write(f"**Giá:** {float(row['price_per_night']):,.0f} VNĐ/đêm")
            st.write(f"**Trạng thái:** {row['status']}")
            
            if row['status'] == 'Đã đặt':
                b_info = pd.read_sql_query(
                    "SELECT customer_name, phone_number, check_in_date FROM bookings WHERE room_number = %s AND status = 'Đang ở'",
                    conn, params=(row['room_number'],)
                )
                if not b_info.empty:
                    st.caption(f"👤 Khách: {b_info.iloc[0]['customer_name']}")
                    st.caption(f"📞 SĐT: {b_info.iloc[0]['phone_number']}")
                    st.caption(f"📅 Nhận: {b_info.iloc[0]['check_in_date']}")
            
            new_status = "Trống" if row['status'] == 'Đã đặt' else "Đã đặt"
            btn_label = f"Chuyển sang {new_status}"
            if st.button(btn_label, key=f"btn_toggle_{row['room_number']}"):
                with conn.cursor() as cur:
                    cur.execute("UPDATE rooms SET status = %s WHERE room_number = %s", (new_status, row['room_number']))
                    conn.commit()
                st.rerun()

            st.markdown("---")

# ==========================================
# 2. CHECK-IN
# ==========================================
elif menu == "Check-in (Nhận phòng)":
    st.title("🔑 Lập phiếu nhận phòng - dmelin hotel")
    
    empty_rooms = pd.read_sql_query("SELECT room_number, room_type, price_per_night FROM rooms WHERE status = 'Trống' ORDER BY room_number ASC", conn)
    
    if empty_rooms.empty:
        st.warning("Hiện tại không còn phòng trống!")
    else:
        r_options = [f"{r['room_number']} - {r['room_type']} ({float(r['price_per_night']):,.0f} VNĐ)" for _, r in empty_rooms.iterrows()]
        
        with st.form("form_checkin"):
            st.subheader("1. Thông tin phòng")
            sel_room = st.selectbox("Chọn phòng trống", r_options)
            
            col_a, col_b = st.columns(2)
            d_in = col_a.date_input("Ngày nhận", datetime.date.today())
            d_out = col_b.date_input("Ngày trả dự kiến", datetime.date.today() + datetime.timedelta(days=1))
            
            st.subheader("2. Thông tin khách hàng")
            c_name = st.text_input("Họ và tên khách *")
            c_id = st.text_input("Số CCCD / Hộ chiếu *")
            
            ca, cb, cc = st.columns(3)
            c_phone = ca.text_input("Số điện thoại")
            c_email = cb.text_input("Email")
            c_nation = cc.text_input("Quốc tịch", value="Việt Nam")
            
            c_notes = st.text_area("Ghi chú đặc biệt")
            
            btn_submit = st.form_submit_button("Thực hiện Check-in")
            
            if btn_submit:
                if not c_name or not c_id:
                    st.error("Vui lòng nhập tên và số CCCD!")
                elif d_out <= d_in:
                    st.error("Ngày trả phòng phải sau ngày nhận!")
                else:
                    r_num = sel_room.split(" - ")[0]
                    with conn.cursor() as cur:
                        cur.execute('''
                            INSERT INTO bookings (
                                room_number, customer_name, customer_id, phone_number, email, 
                                nationality, notes, check_in_date, check_out_date, status
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Đang ở')
                        ''', (r_num, c_name, c_id, c_phone, c_email, c_nation, c_notes, d_in, d_out))
                        
                        cur.execute("UPDATE rooms SET status = 'Đã đặt' WHERE room_number = %s", (r_num,))
                        conn.commit()
                    st.success(f"Check-in thành công cho phòng {r_num}!")
                    st.rerun()

# ==========================================
# 3. DỊCH VỤ & CHECK-OUT
# ==========================================
elif menu == "Dịch vụ & Check-out":
    st.title("🛠️ Dịch vụ phát sinh & Thanh toán")
    
    act_bookings = pd.read_sql_query("SELECT id, room_number, customer_name FROM bookings WHERE status = 'Đang ở' ORDER BY id DESC", conn)
    
    if act_bookings.empty:
        st.info("Hiện không có phòng nào đang lưu trú.")
    else:
        b_dict = {f"Phòng {r['room_number']} - {r['customer_name']} (Mã: {r['id']})": r['id'] for _, r in act_bookings.iterrows()}
        sel_label = st.selectbox("Chọn lượt lưu trú cần xử lý", list(b_dict.keys()))
        sel_id = int(b_dict[sel_label])
        
        tab_srv, tab_pay = st.tabs(["➕ Thêm dịch vụ", "💳 Check-out & Thanh toán"])
        
        with tab_srv:
            with st.form("form_srv"):
                s_name = st.text_input("Tên dịch vụ", value="Nước suối")
                s_price = st.number_input("Đơn giá (VNĐ)", min_value=0, value=15000, step=5000)
                s_qty = st.number_input("Số lượng", min_value=1, value=1, step=1)
                
                if st.form_submit_button("Thêm dịch vụ"):
                    tot = s_price * s_qty
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO services (booking_id, service_name, price, quantity, total) VALUES (%s, %s, %s, %s, %s)",
                                    (sel_id, s_name, s_price, s_qty, tot))
                        conn.commit()
                    st.success(f"Đã thêm {s_qty}x {s_name}.")
            
            srv_df = pd.read_sql_query("SELECT service_name as \"Dịch vụ\", price as \"Đơn giá\", quantity as \"Số lượng\", total as \"Thành tiền\" FROM services WHERE booking_id = %s", conn, params=(sel_id,))
            if not srv_df.empty:
                st.dataframe(srv_df)

        with tab_pay:
            b_info = pd.read_sql_query('''
                SELECT b.*, r.price_per_night 
                FROM bookings b JOIN rooms r ON b.room_number = r.room_number 
                WHERE b.id = %s
            ''', conn, params=(sel_id,)).iloc[0]
            
            d1 = pd.to_datetime(b_info['check_in_date']).date()
            d2 = datetime.date.today()
            days = max((d2 - d1).days, 1)
            
            r_cost = days * float(b_info['price_per_night'])
            s_cost_df = pd.read_sql_query("SELECT SUM(total) as stot FROM services WHERE booking_id = %s", conn, params=(sel_id,))
            s_cost = float(s_cost_df.iloc[0]['stot']) if s_cost_df.iloc[0]['stot'] else 0.0
            
            g_total = r_cost + s_cost
            
            st.write(f"**Khách hàng:** {b_info['customer_name']} | **CCCD:** {b_info['customer_id']} | **SĐT:** {b_info['phone_number']}")
            st.write(f"**Phòng:** {b_info['room_number']} | **Ngày vào:** {b_info['check_in_date']} | **Ngày trả:** {d2}")
            st.markdown("---")
            st.write(f"Tiền phòng ({days} đêm): **{r_cost:,.0f} VNĐ**")
            st.write(f"Tiền dịch vụ: **{s_cost:,.0f} VNĐ**")
            st.markdown(f"### 💵 **Tổng thanh toán:** :red[{g_total:,.0f} VNĐ]")
            
            if st.button("Xác nhận thanh toán & Trả phòng", type="primary"):
                with conn.cursor() as cur:
                    cur.execute('''
                        UPDATE bookings 
                        SET check_out_date = %s, status = 'Đã trả phòng', total_room_cost = %s, service_cost = %s, total_amount = %s
                        WHERE id = %s
                    ''', (d2, r_cost, s_cost, g_total, sel_id))
                    cur.execute("UPDATE rooms SET status = 'Trống' WHERE room_number = %s", (b_info['room_number'],))
                    conn.commit()
                st.balloons()
                st.success("Thanh toán thành công!")
                st.rerun()

# ==========================================
# 4. QUẢN LÝ KHÁCH LƯU TRÚ
# ==========================================
elif menu == "Quản lý khách lưu trú":
    st.title("📇 Hồ sơ khách lưu trú - dmelin hotel")
    
    kw = st.text_input("🔍 Tìm theo Tên, CCCD hoặc SĐT")
    sql = '''
        SELECT 
            id as "Mã Phiếu", customer_name as "Họ tên", customer_id as "CCCD/Hộ chiếu",
            phone_number as "SĐT", email as "Email", nationality as "Quốc tịch",
            room_number as "Phòng", check_in_date as "Ngày vào", check_out_date as "Ngày ra",
            total_amount as "Tổng chi tiêu (VNĐ)", status as "Trạng thái"
        FROM bookings
    '''
    if kw:
        sql += f" WHERE customer_name ILIKE '%%{kw}%%' OR customer_id ILIKE '%%{kw}%%' OR phone_number ILIKE '%%{kw}%%'"
    sql += " ORDER BY id DESC"
    
    st.dataframe(pd.read_sql_query(sql, conn))

# ==========================================
# 5. THỐNG KÊ DOANH THU
# ==========================================
elif menu == "Thống kê doanh thu":
    st.title("📊 Thống kê doanh thu - dmelin hotel")
    
    hist_df = pd.read_sql_query('''
        SELECT b.*, r.room_type 
        FROM bookings b JOIN rooms r ON b.room_number = r.room_number 
        WHERE b.status = 'Đã trả phòng'
        ORDER BY b.check_out_date DESC
    ''', conn)
    
    act_df = pd.read_sql_query('''
        SELECT b.*, r.room_type, r.price_per_night 
        FROM bookings b JOIN rooms r ON b.room_number = r.room_number 
        WHERE b.status = 'Đang ở'
    ''', conn)
    
    est_rev = 0
    if not act_df.empty:
        temp_list = []
        for _, r in act_df.iterrows():
            d1 = pd.to_datetime(r['check_in_date']).date()
            days = max((datetime.date.today() - d1).days, 1)
            sc = pd.read_sql_query("SELECT SUM(total) as stot FROM services WHERE booking_id = %s", conn, params=(int(r['id']),)).iloc[0]['stot'] or 0
            temp_list.append((days * float(r['price_per_night'])) + float(sc))
        act_df['Doanh thu tạm tính (VNĐ)'] = temp_list
        est_rev = sum(temp_list)

    real_rev = float(hist_df['total_amount'].sum()) if not hist_df.empty else 0.0
    room_rev = float(hist_df['total_room_cost'].sum()) if not hist_df.empty else 0.0
    srv_rev = float(hist_df['service_cost'].sum()) if not hist_df.empty else 0.0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("THỰC THU (Đã check-out)", f"{real_rev:,.0f} VNĐ")
    m2.metric("DỰ KIẾN (Đang lưu trú)", f"{est_rev:,.0f} VNĐ")
    m3.metric("Doanh thu tiền phòng", f"{room_rev:,.0f} VNĐ")
    m4.metric("Doanh thu dịch vụ", f"{srv_rev:,.0f} VNĐ")
    
    st.markdown("---")
    
    t1, t2, t3 = st.tabs(["🔴 Phòng đang lưu trú", "🟢 Lịch sử đã checkout", "👑 Doanh thu theo Khách hàng VIP"])
    
    with t1:
        if act_df.empty:
            st.info("Không có phòng nào đang ở.")
        else:
            disp = act_df[['room_number', 'room_type', 'customer_name', 'phone_number', 'check_in_date', 'Doanh thu tạm tính (VNĐ)']]
            disp.columns = ['Số phòng', 'Loại phòng', 'Khách hàng', 'SĐT', 'Ngày vào', 'Doanh thu dự kiến (VNĐ)']
            st.dataframe(disp)
            
    with t2:
        if hist_df.empty:
            st.info("Chưa có lịch sử thanh toán.")
        else:
            ca, cb = st.columns(2)
            with ca:
                st.write("**Doanh thu theo ngày**")
                d_rev = hist_df.groupby('check_out_date')['total_amount'].sum().reset_index()
                d_rev.columns = ['Ngày', 'Doanh thu']
                st.bar_chart(d_rev.set_index('Ngày'))
            with cb:
                st.write("**Doanh thu theo loại phòng**")
                t_rev = hist_df.groupby('room_type')['total_amount'].sum().reset_index()
                t_rev.columns = ['Loại phòng', 'Doanh thu']
                st.dataframe(t_rev)
            st.dataframe(hist_df)

    with t3:
        if hist_df.empty:
            st.info("Chưa có dữ liệu.")
        else:
            vip_df = hist_df.groupby(['customer_name', 'customer_id', 'phone_number']).agg(
                so_luot=('id', 'count'),
                tong_tien=('total_amount', 'sum'),
                tien_phong=('total_room_cost', 'sum'),
                tien_dv=('service_cost', 'sum')
            ).reset_index().sort_values(by='tong_tien', ascending=False)
            
            vip_df.columns = ['Họ tên khách', 'CCCD / Hộ chiếu', 'Số điện thoại', 'Số lượt ở', 'Tổng đóng góp (VNĐ)', 'Tiền phòng (VNĐ)', 'Tiền dịch vụ (VNĐ)']
            st.dataframe(vip_df)

# ==========================================
# 6. CẤU HÌNH PHÒNG
# ==========================================
elif menu == "Cấu hình phòng":
    st.title("⚙️ Cấu hình danh mục phòng - dmelin hotel")
    
    with st.form("form_add_room"):
        st.subheader("Thêm phòng mới")
        r_num = st.text_input("Số phòng")
        r_type = st.selectbox("Loại phòng", ["Đơn Standard", "Đôi Deluxe", "VIP Suite", "Gia đình"])
        r_price = st.number_input("Giá phòng / đêm (VNĐ)", min_value=100000, value=500000, step=50000)
        
        if st.form_submit_button("Thêm phòng"):
            if not r_num:
                st.error("Vui lòng nhập số phòng!")
            else:
                try:
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO rooms (room_number, room_type, price_per_night, status) VALUES (%s, %s, %s, 'Trống')", (r_num, r_type, r_price))
                        conn.commit()
                    st.success(f"Đã thêm phòng {r_num}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi thêm phòng (Có thể số phòng đã tồn tại): {e}")

    st.markdown("---")
    st.subheader("Danh sách tất cả các phòng")
    st.dataframe(pd.read_sql_query("SELECT room_number as \"Số phòng\", room_type as \"Loại phòng\", price_per_night as \"Giá/đêm (VNĐ)\", status as \"Trạng thái\" FROM rooms ORDER BY room_number ASC", conn))
