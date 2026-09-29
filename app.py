import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# ---------------------------------------------------------
# CONFIG & INITIALIZATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Hệ Thống Quản Lý Khách Sạn Pro",
    page_icon="🏨",
    layout="wide"
)

# Khởi tạo dữ liệu mẫu trong Session State (mô phỏng CSDL)
if 'rooms' not in st.session_state:
    st.session_state.rooms = [
        {"room_num": "101", "type": "Đơn", "price": 500000, "status": "Trống", "guest_name": "", "check_in": None, "nights": 1},
        {"room_num": "102", "type": "Đơn", "price": 500000, "status": "Có khách", "guest_name": "Nguyễn Văn A", "check_in": date.today(), "nights": 2},
        {"room_num": "103", "type": "Đôi", "price": 800000, "status": "Trống", "guest_name": "", "check_in": None, "nights": 1},
        {"room_num": "201", "type": "Đôi", "price": 800000, "status": "Đang dọn", "guest_name": "", "check_in": None, "nights": 1},
        {"room_num": "202", "type": "VIP", "price": 1500000, "status": "Có khách", "guest_name": "Tran Thi B", "check_in": date.today(), "nights": 3},
        {"room_num": "203", "type": "VIP", "price": 1500000, "status": "Trống", "guest_name": "", "check_in": None, "nights": 1},
    ]

if 'revenue_history' not in st.session_state:
    st.session_state.revenue_history = [
        {"date": "2026-09-27", "amount": 2500000, "room": "102"},
        {"date": "2026-09-28", "amount": 1500000, "room": "202"},
    ]

# ---------------------------------------------------------
# SIDEBAR NAVIGATION
# ---------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/hotel-check-in.png", width=80)
st.sidebar.title("Quản Lý Khách Sạn")
page = st.sidebar.radio("Danh mục chức năng", [
    "📌 Sơ đồ phòng & Trạng thái",
    "🔑 Check-in / Check-out",
    "⚙️ Quản lý danh mục phòng",
    "📊 Báo cáo & Thống kê"
])

# ---------------------------------------------------------
# PAGE 1: SƠ ĐỒ PHÒNG
# ---------------------------------------------------------
if page == "📌 Sơ đồ phòng & Trạng thái":
    st.title("📌 Sơ Đồ Phòng & Trạng Thái Trực Quan")
    
    # Chỉ số KPI nhanh
    df_rooms = pd.DataFrame(st.session_state.rooms)
    total_rooms = len(df_rooms)
    occupied = len(df_rooms[df_rooms['status'] == 'Có khách'])
    available = len(df_rooms[df_rooms['status'] == 'Trống'])
    cleaning = len(df_rooms[df_rooms['status'] == 'Đang dọn'])
    
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    col_kpi1.metric("Tổng số phòng", total_rooms)
    col_kpi2.metric("Đang có khách", occupied, delta=f"{int(occupied/total_rooms*100)}% công suất")
    col_kpi3.metric("Phòng trống", available)
    col_kpi4.metric("Đang dọn dẹp", cleaning)
    
    st.divider()
    
    # Bộ lọc trạng thái
    status_filter = st.selectbox("Lọc theo trạng thái", ["Tất cả", "Trống", "Có khách", "Đang dọn"])
    
    # Lưới hiển thị các phòng
    cols = st.columns(3)
    filtered_rooms = st.session_state.rooms if status_filter == "Tất cả" else [r for r in st.session_state.rooms if r['status'] == status_filter]
    
    color_map = {
        "Trống": "#28a745",
        "Có khách": "#dc3545",
        "Đang dọn": "#ffc107"
    }

    for idx, room in enumerate(filtered_rooms):
        with cols[idx % 3]:
            bg_color = color_map.get(room['status'], "#ffffff")
            text_color = "#ffffff" if room['status'] in ["Trống", "Có khách"] else "#000000"
            
            st.markdown(
                f"""
                <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; color: {text_color}; margin-bottom: 15px;">
                    <h3 style="margin: 0; color: {text_color};">Phòng {room['room_num']} - {room['type']}</h3>
                    <p style="margin: 5px 0;"><b>Trạng thái:</b> {room['status']}</p>
                    <p style="margin: 5px 0;"><b>Giá phòng:</b> {room['price']:,} VNĐ/đêm</p>
                    {'<p style="margin: 5px 0;"><b>Khách hàng:</b> ' + str(room['guest_name']) + '</p>' if room['guest_name'] else ''}
                </div>
                """,
                unsafe_allow_html=True
            )

# ---------------------------------------------------------
# PAGE 2: CHECK-IN / CHECK-OUT
# ---------------------------------------------------------
elif page == "🔑 Check-in / Check-out":
    st.title("🔑 Nghiệp Vụ Check-in / Check-out")
    
    tab1, tab2, tab3 = st.tabs(["Check-in (Nhận phòng)", "Check-out (Trả phòng)", "Đổi trạng thái phòng"])
    
    # Tab Check-in
    with tab1:
        st.subheader("Làm thủ tục Nhận phòng")
        empty_rooms = [r['room_num'] for r in st.session_state.rooms if r['status'] == "Trống"]
        
        if empty_rooms:
            with st.form("checkin_form"):
                selected_room = st.selectbox("Chọn phòng trống", empty_rooms)
                guest_name = st.text_input("Tên khách hàng")
                check_in_date = st.date_input("Ngày nhận phòng", value=date.today())
                nights = st.number_input("Số đêm lưu trú", min_value=1, value=1)
                
                submit_checkin = st.form_submit_button("Xác nhận Check-in")
                
                if submit_checkin:
                    if guest_name.strip() == "":
                        st.error("Vui lòng nhập tên khách hàng!")
                    else:
                        for room in st.session_state.rooms:
                            if room['room_num'] == selected_room:
                                room['status'] = "Có khách"
                                room['guest_name'] = guest_name
                                room['check_in'] = check_in_date
                                room['nights'] = nights
                                break
                        st.success(f"Check-in thành công phòng {selected_room} cho khách {guest_name}!")
                        st.rerun()
        else:
            st.warning("Hiện tại không có phòng nào trống!")

    # Tab Check-out
    with tab2:
        st.subheader("Làm thủ tục Trả phòng & Thanh toán")
        occupied_rooms = [r['room_num'] for r in st.session_state.rooms if r['status'] == "Có khách"]
        
        if occupied_rooms:
            selected_out_room = st.selectbox("Chọn phòng trả", occupied_rooms)
            current_room = next(r for r in st.session_state.rooms if r['room_num'] == selected_out_room)
            
            total_bill = current_room['price'] * current_room['nights']
            
            st.info(f"""
            **Thông tin thanh toán phòng {selected_out_room}:**
            - Khách hàng: {current_room['guest_name']}
            - Số đêm: {current_room['nights']}
            - Đơn giá: {current_room['price']:,} VNĐ
            - **Tổng tiền: {total_bill:,} VNĐ**
            """)
            
            if st.button("Xác nhận thanh toán & Check-out"):
                # Lưu lịch sử doanh thu
                st.session_state.revenue_history.append({
                    "date": date.today().strftime("%Y-%m-%d"),
                    "amount": total_bill,
                    "room": selected_out_room
                })
                # Cập nhật trạng thái phòng thành Đang dọn
                for room in st.session_state.rooms:
                    if room['room_num'] == selected_out_room:
                        room['status'] = "Đang dọn"
                        room['guest_name'] = ""
                        room['check_in'] = None
                        room['nights'] = 1
                        break
                st.success(f"Thanh toán thành công phòng {selected_out_room}. Phòng chuyển sang trạng thái Đang dọn!")
                st.rerun()
        else:
            st.info("Hiện không có phòng nào đang có khách.")

    # Tab Đổi trạng thái (Ví dụ: Dọn phòng xong)
    with tab3:
        st.subheader("Cập nhật trạng thái Vệ sinh/Dọn dẹp")
        room_to_update = st.selectbox("Chọn phòng cần cập nhật", [r['room_num'] for r in st.session_state.rooms])
        new_status = st.selectbox("Trạng thái mới", ["Trống", "Đang dọn", "Bảo trì"])
        
        if st.button("Cập nhật trạng thái"):
            for room in st.session_state.rooms:
                if room['room_num'] == room_to_update:
                    room['status'] = new_status
                    break
            st.success(f"Đã cập nhật phòng {room_to_update} sang trạng thái {new_status}!")
            st.rerun()

# ---------------------------------------------------------
# PAGE 3: QUẢN LÝ DANH MỤC PHÒNG
# ---------------------------------------------------------
elif page == "⚙️ Quản lý danh mục phòng":
    st.title("⚙️ Quản Lý Sơ Đồ Danh Mục Phòng")
    
    # Hiển thị bảng hiện tại
    df_rooms = pd.DataFrame(st.session_state.rooms)
    st.dataframe(df_rooms[['room_num', 'type', 'price', 'status']], use_container_width=True)
    
    st.divider()
    st.subheader("Thêm phòng mới")
    with st.form("add_room_form"):
        col1, col2, col3 = st.columns(3)
        new_num = col1.text_input("Số phòng (VD: 301)")
        new_type = col2.selectbox("Loại phòng", ["Đơn", "Đôi", "VIP", "Family"])
        new_price = col3.number_input("Giá phòng (VNĐ/đêm)", step=50000, value=500000)
        
        add_submit = st.form_submit_button("Thêm phòng")
        if add_submit:
            if any(r['room_num'] == new_num for r in st.session_state.rooms):
                st.error("Số phòng này đã tồn tại!")
            elif new_num.strip() == "":
                st.error("Số phòng không được để trống!")
            else:
                st.session_state.rooms.append({
                    "room_num": new_num,
                    "type": new_type,
                    "price": new_price,
                    "status": "Trống",
                    "guest_name": "",
                    "check_in": None,
                    "nights": 1
                })
                st.success(f"Đã thêm phòng {new_num} thành công!")
                st.rerun()

# ---------------------------------------------------------
# PAGE 4: BÁO CÁO & THỐNG KÊ
# ---------------------------------------------------------
elif page == "📊 Báo cáo & Thống kê":
    st.title("📊 Báo Cáo Hiệu Quả Kinh Doanh")
    
    df_rev = pd.DataFrame(st.session_state.revenue_history)
    
    if not df_rev.empty:
        total_rev = df_rev['amount'].sum()
        st.metric("Tổng doanh thu ghi nhận", f"{total_rev:,} VNĐ")
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Doanh thu theo ngày")
            fig_bar = px.bar(df_rev, x='date', y='amount', text_auto='.2s', labels={'date': 'Ngày', 'amount': 'Doanh thu (VNĐ)'})
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_chart2:
            st.subheader("Cơ cấu trạng thái phòng hiện tại")
            df_status = pd.DataFrame(st.session_state.rooms)['status'].value_counts().reset_index()
            df_status.columns = ['Trạng thái', 'Số lượng']
            fig_pie = px.pie(df_status, names='Trạng thái', values='Số lượng', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu doanh thu.")
