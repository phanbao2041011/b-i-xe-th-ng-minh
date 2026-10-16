import streamlit as st

# ==========================================
# 1. CẤU HÌNH TRANG WEB
# ==========================================
st.set_page_config(
    page_title="Hệ thống Bãi đỗ xe Tự động",
    page_icon="🚗",
    layout="wide"
)

# ==========================================
# 2. KHỞI TẠO BỘ NHỚ BÃI ĐỖ XE (60 Ô / TẦNG)
# ==========================================
if "parking_slots" not in st.session_state:
    slots = []
    floors = ["Tầng 1", "Tầng B1", "Tầng B2"]
    
    for floor in floors:
        for y in range(1, 7):
            for x in range(1, 11):
                slot_id = f"X{x}Y{y}"
                is_priority_slot = True if (floor == "Tầng 1" and x <= 2) else False
                
                slots.append({
                    "floor": floor,
                    "id": slot_id,
                    "x": x,
                    "y": y,
                    "status": "TRỐNG",  # Có 3 trạng thái: TRỐNG, ĐÃ ĐỖ, ĐÃ KHÓA
                    "is_priority_slot": is_priority_slot
                })
                
    st.session_state.parking_slots = slots

if "last_assigned_slot" not in st.session_state:
    st.session_state.last_assigned_slot = None

# ==========================================
# 3. THANH BÊN (SIDEBAR) - KHAI BÁO & QUẢN TRỊ
# ==========================================
st.sidebar.header("📋 Khai báo Xe vào Cổng")

is_priority = st.sidebar.checkbox("⚡ Đối tượng Ưu tiên")

duration = st.sidebar.number_input(
    "⏱️ Thời gian đỗ dự kiến (giờ):",
    min_value=0.0,
    max_value=168.0,
    value=2.0,
    step=0.5
)

# --- CHẾ ĐỘ QUẢN TRỊ VIÊN (ADMIN MODE) ---
st.sidebar.markdown("---")
admin_mode = st.sidebar.checkbox("🛡️ Chế độ Quản trị viên (Admin)")

if admin_mode:
    st.sidebar.subheader("⚙️ Quản lý Khóa / Mở ô đỗ")
    selected_floor_admin = st.sidebar.selectbox("Chọn tầng:", ["Tầng 1", "Tầng B1", "Tầng B2"])
    
    # Lấy danh sách ID các ô thuộc tầng đang chọn
    floor_slot_ids = [s["id"] for s in st.session_state.parking_slots if s["floor"] == selected_floor_admin]
    
    selected_slots_to_toggle = st.sidebar.multiselect(
        "Chọn các ô cần thao tác:",
        options=floor_slot_ids,
        placeholder="Chọn một hoặc nhiều ô..."
    )
    
    col_lock, col_unlock = st.sidebar.columns(2)
    
    # Nút Khóa ô
    if col_lock.button("🔒 Khóa ô", use_container_width=True):
        if selected_slots_to_toggle:
            for s in st.session_state.parking_slots:
                if s["floor"] == selected_floor_admin and s["id"] in selected_slots_to_toggle:
                    s["status"] = "ĐÃ KHÓA"
            st.sidebar.success(f"Đã KHÓA {len(selected_slots_to_toggle)} ô tại {selected_floor_admin}!")
            st.rerun()
            
    # Nút Mở khóa ô
    if col_unlock.button("🔓 Mở khóa", use_container_width=True):
        if selected_slots_to_toggle:
            for s in st.session_state.parking_slots:
                if s["floor"] == selected_floor_admin and s["id"] in selected_slots_to_toggle:
                    s["status"] = "TRỐNG"
            st.sidebar.success(f"Đã MỞ KHÓA {len(selected_slots_to_toggle)} ô tại {selected_floor_admin}!")
            st.rerun()

    # Nút Reset bãi đỗ xe
    if st.sidebar.button("🔄 Reset toàn bộ bãi đỗ", use_container_width=True):
        for s in st.session_state.parking_slots:
            s["status"] = "TRỐNG"
        st.session_state.last_assigned_slot = None
        st.sidebar.info("Đã đặt lại tất cả các ô về trạng thái TRỐNG!")
        st.rerun()

st.sidebar.markdown("---")

# ==========================================
# 4. LOGIC THUẬT TOÁN PHÂN BỔ VỊ TRÍ
# ==========================================
def find_best_slot(duration, is_priority):
    all_slots = st.session_state.parking_slots
    floors_order = ["Tầng 1", "Tầng B1", "Tầng B2"]
    
    # CASE 1: ĐỐI TƯỢNG ƯU TIÊN -> Ưu tiên ô X1, X2 tại Tầng 1
    if is_priority:
        priority_slots = [
            s for s in all_slots 
            if s["floor"] == "Tầng 1" and s["is_priority_slot"] and s["status"] == "TRỐNG"
        ]
        if priority_slots:
            priority_slots[0]["status"] = "ĐÃ ĐỖ"
            return priority_slots[0]

    # CASE 2: XÁC ĐỊNH TẦNG MỤC TIÊU BAN ĐẦU THEO THỜI GIAN
    if is_priority or duration <= 2.0:
        target_floor = "Tầng 1"   # Ngắn hạn (<= 2h)
    elif duration <= 8.0:
        target_floor = "Tầng B1"  # Trung hạn (2 - 8h)
    else:
        target_floor = "Tầng B2"  # Dài hạn (> 8h)

    start_idx = floors_order.index(target_floor)
    search_order = floors_order[start_idx:] + floors_order[:start_idx]

    # DUYỆT TỪNG TẦNG THEO THỨ TỰ (Tự động bỏ qua các ô status == "ĐÃ KHÓA")
    for current_floor in search_order:
        available = [
            s for s in all_slots 
            if s["floor"] == current_floor and s["status"] == "TRỐNG"
        ]

        if current_floor == "Tầng 1" and not is_priority:
            normal_t1 = [s for s in available if not s["is_priority_slot"]]
            if normal_t1:
                available = normal_t1

        if available:
            selected_slot = available[0]
            selected_slot["status"] = "ĐÃ ĐỖ"

            if current_floor != target_floor:
                st.sidebar.warning(f"⚠️ **{target_floor}** đã hết chỗ khả dụng! Đã tự động chuyển ô đỗ sang **{current_floor}**.")

            return selected_slot

    return None

# NÚT ĐỖ XE THEO GỢI Ý
if st.sidebar.button("🎯 ĐỖ XE THEO GỢI Ý", use_container_width=True):
    slot = find_best_slot(duration, is_priority)
    if slot:
        st.session_state.last_assigned_slot = slot
        st.sidebar.success(f"✅ Gán ô thành công: **{slot['id']}** (**{slot['floor']}**)")
    else:
        st.session_state.last_assigned_slot = "FULL"
        st.sidebar.error("⛔ **RẤT TIẾC: TOÀN BỘ BÃI ĐỖ XE ĐÃ HẾT CHỖ TRỐNG KHẢ DỤNG!**")

# ==========================================
# 5. HIỂN THỊ TIÊU ĐỀ & THỐNG KÊ TỔNG QUAN
# ==========================================
st.title("🚗 Hệ thống Tối ưu Bãi đỗ xe Tự động")

total_slots = len(st.session_state.parking_slots)
occupied_slots = sum(1 for s in st.session_state.parking_slots if s["status"] == "ĐÃ ĐỖ")
locked_slots = sum(1 for s in st.session_state.parking_slots if s["status"] == "ĐÃ KHÓA")
free_slots = total_slots - occupied_slots - locked_slots

col1, col2, col3, col4 = st.columns(4)
col1.metric("Tổng quy mô", f"{total_slots} ô")
col2.metric("Ô còn trống", f"{free_slots} ô")
col3.metric("Xe đã đỗ", f"{occupied_slots} xe")
col4.metric("Ô tạm khóa", f"{locked_slots} ô")

st.divider()

# ==========================================
# 6. GIAO DIỆN SƠ ĐỒ SÀN & CHỈ DẪN HỆ THỐNG
# ==========================================
col_map, col_info = st.columns([3.2, 1])

def render_custom_grid_map(floor_name):
    slots = [s for s in st.session_state.parking_slots if s["floor"] == floor_name]
    last_assigned = st.session_state.last_assigned_slot

    top_rows = [6, 5, 4]
    bottom_rows = [3, 2, 1]

    def build_grid_html(row_list):
        grid_html = '<div style="display: grid; grid-template-columns: repeat(10, 1fr); gap: 6px; margin-bottom: 8px;">'
        for y in row_list:
            for x in range(1, 11):
                slot = next((s for s in slots if s["x"] == x and s["y"] == y), None)
                if not slot:
                    continue
                
                is_last = (isinstance(last_assigned, dict) and last_assigned.get("id") == slot["id"] and last_assigned.get("floor") == floor_name)
                
                if is_last:
                    bg_color = "#c6f6d5"
                    border_color = "#38a169"
                    text_color = "#22543d"
                    status_text = "CHỌN 🎯"
                elif slot["status"] == "ĐÃ KHÓA":
                    bg_color = "#e2e8f0"
                    border_color = "#a0aec0"
                    text_color = "#4a5568"
                    status_text = "🔒 KHÓA"
                elif slot["status"] == "ĐÃ ĐỖ":
                    bg_color = "#fed7d7"
                    border_color = "#e53e3e"
                    text_color = "#9b2c2c"
                    status_text = "ĐÃ ĐỖ"
                elif slot["is_priority_slot"]:
                    bg_color = "#fefcbf"
                    border_color = "#d69e2e"
                    text_color = "#744210"
                    status_text = "ƯU TIÊN ⭐"
                else:
                    bg_color = "#ffffff"
                    border_color = "#cbd5e0"
                    text_color = "#2d3748"
                    status_text = "TRỐNG"

                grid_html += f'<div style="background-color: {bg_color}; border: 1.5px solid {border_color}; border-radius: 6px; padding: 6px 2px; text-align: center; font-family: sans-serif; box-shadow: 0 1px 2px rgba(0,0,0,0.05);"><div style="font-size: 11px; font-weight: 800; color: {text_color};">{slot["id"]}</div><div style="font-size: 9px; font-weight: 700; color: {text_color}; margin-top: 2px;">{status_text}</div></div>'
        grid_html += '</div>'
        return grid_html

    map_html = f'''<div style="background-color: #ffffff; border-radius: 12px; padding: 18px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
{build_grid_html(top_rows)}
<div style="display: flex; align-items: center; justify-content: space-between; background-color: #edf2f7; border: 2px dashed #cbd5e0; border-radius: 8px; padding: 8px 14px; margin: 12px 0; font-family: sans-serif;">
<span style="background-color: #fefcbf; color: #744210; border: 1px solid #d69e2e; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">🚪 CỔNG VÀO</span>
<span style="font-size: 12px; font-weight: bold; color: #4a5568; letter-spacing: 1px;">🚗 LÀN ĐƯỜNG CHÍNH (MAIN DRIVEWAY) ──────────────────►</span>
<span style="background-color: #c6f6d5; color: #22543d; border: 1px solid #38a169; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">🚪 LỐI RA</span>
</div>
{build_grid_html(bottom_rows)}
</div>'''

    st.markdown(map_html, unsafe_allow_html=True)

# --- CỘT TRÁI: SƠ ĐỒ BÃI ĐỖ XE ---
with col_map:
    st.subheader("🗺️ Sơ đồ Mặt bằng Bãi đỗ xe")
    
    tab1, tab2, tab3 = st.tabs([
        "Tầng 1 (Cổng Ra/Vào & Ngắn hạn)", 
        "Tầng B1 (Trung hạn)", 
        "Tầng B2 (Dài hạn)"
    ])
    
    with tab1:
        render_custom_grid_map("Tầng 1")
    with tab2:
        render_custom_grid_map("Tầng B1")
    with tab3:
        render_custom_grid_map("Tầng B2")

# --- CỘT PHẢI: CHỈ DẪN HỆ THỐNG & KHAI BÁO ---
with col_info:
    st.subheader("📌 Chỉ dẫn Hệ thống")
    
    last_slot = st.session_state.last_assigned_slot
    
    if last_slot == "FULL":
        st.error("⛔ **THÔNG BÁO TỪ HỆ THỐNG:**\n\nHiện tại tất cả các tầng (**Tầng 1, B1, B2**) đều đã **KÍN CHỖ HOẶC ĐÃ BỊ KHÓA**. Vui lòng quay lại sau!")
    elif isinstance(last_slot, dict):
        st.success(f"🎯 **Ô CHỌN GẮN: {last_slot['id']}**\n\n*(Thuộc {last_slot['floor']})*")
    else:
        st.info("🎯 **Chưa có ô đỗ nào được chọn.**\n\nNhấn nút 'ĐỖ XE THEO GỢI Ý' ở thanh bên để gán vị trí.")

    st.markdown("---")
    st.subheader("ℹ️ Thông tin Khai báo")
    
    st.markdown(f"""
    * **Đối tượng:** {"⚡ Ưu tiên" if is_priority else "🚗 Thông thường"}
    * **Thời gian đỗ:** `{duration} giờ`
    * **Tầng hầm dự kiến:** `{ "Tầng 1" if is_priority or duration <= 2 else ("Tầng B1" if duration <= 8 else "Tầng B2") }`
    """)
    
    st.markdown("---")
    st.caption("**Chú thích màu sắc:**")
    st.caption("🟢 **TRỐNG**: Ô đỗ còn trống")
    st.caption("🔴 **ĐÃ ĐỖ**: Ô đỗ đã có xe")
    st.caption("🔒 **KHÓA**: Ô tạm khóa / Bảo trì")
    st.caption("🟡 **ƯU TIÊN**: Ô đắc địa gần ra/vào (Tầng 1)")
    st.caption("🟢 **CHỌN 🎯**: Vị trí hệ thống vừa gán")