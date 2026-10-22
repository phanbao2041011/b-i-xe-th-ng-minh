import streamlit as st

# ==========================================
# 1. CẤU HÌNH TRANG WEB
# ==========================================
st.set_page_config(
    page_title="Hệ thống AGV Smart Parking - Block Model",
    page_icon="🤖",
    layout="wide"
)

# ==========================================
# 2. KHỞI TẠO BỘ NHỚ MÔ HÌNH BLOCK (60 Ô / TẦNG)
# ==========================================
if "parking_slots" not in st.session_state:
    slots = []
    floors = ["Tầng 1", "Tầng B1", "Tầng B2"]
    
    # Định nghĩa 4 Block xếp hình cho mỗi tầng
    # Block A: Gần Cổng AGV nhất (D=1) | Block B: (D=2) | Block C: (D=3) | Block D: Sâu nhất (D=4)
    blocks_def = {
        "Block A": {"dist": 1, "cols": range(1, 4), "rows": range(4, 7), "color": "#ebf8ff"},
        "Block B": {"dist": 2, "cols": range(4, 8), "rows": range(4, 7), "color": "#f0fff4"},
        "Block C": {"dist": 3, "cols": range(1, 5), "rows": range(1, 4), "color": "#fffaf0"},
        "Block D": {"dist": 4, "cols": range(5, 11), "rows": range(1, 4), "color": "#faf5ff"}
    }
    
    for floor in floors:
        for block_name, b_info in blocks_def.items():
            for y in b_info["rows"]:
                for x in b_info["cols"]:
                    # Ô thuộc Block A ở Tầng 1 nằm ngay lối vào là ô ưu tiên
                    is_priority_slot = True if (floor == "Tầng 1" and block_name == "Block A" and y == 4 and x <= 2) else False
                    
                    slots.append({
                        "floor": floor,
                        "id": f"X{x}Y{y}",
                        "x": x,
                        "y": y,
                        "block": block_name,
                        "distance": b_info["dist"],
                        "status": "TRỐNG",  # TRỐNG, ĐÃ ĐỖ, ĐÃ KHÓA
                        "is_priority_slot": is_priority_slot
                    })
                
    st.session_state.parking_slots = slots

if "last_assigned_slot" not in st.session_state:
    st.session_state.last_assigned_slot = None

# ==========================================
# 3. THANH BÊN (SIDEBAR) - KHAI BÁO THÔNG TIN XE & ROBOT AGV
# ==========================================
st.sidebar.header("📋 Khai báo Thông tin Xe vào Cổng")

is_priority = st.sidebar.checkbox("⚡ Đối tượng Ưu tiên")

duration = st.sidebar.number_input(
    "⏱️ Thời gian đỗ dự kiến (giờ):",
    min_value=0.1,
    max_value=168.0,
    value=2.0,
    step=0.5
)

weight = st.sidebar.number_input(
    "⚖️ Khối lượng xe (kg):",
    min_value=500,
    max_value=5000,
    value=1500,
    step=100,
    help="Robot AGV sẽ tính toán lượng điện năng tiêu thụ dựa trên khối lượng xe."
)

# --- CHẾ ĐỘ QUẢN TRỊ VIÊN (ADMIN) ---
st.sidebar.markdown("---")
admin_mode = st.sidebar.checkbox("🛡️ Chế độ Quản trị viên (Admin)")

if admin_mode:
    st.sidebar.subheader("⚙️ Quản lý Khóa / Mở ô đỗ")
    selected_floor_admin = st.sidebar.selectbox("Chọn tầng:", ["Tầng 1", "Tầng B1", "Tầng B2"])
    
    floor_slot_ids = [s["id"] for s in st.session_state.parking_slots if s["floor"] == selected_floor_admin]
    
    selected_slots_to_toggle = st.sidebar.multiselect(
        "Chọn các ô cần thao tác:",
        options=floor_slot_ids,
        placeholder="Chọn một hoặc nhiều ô..."
    )
    
    col_lock, col_unlock = st.sidebar.columns(2)
    
    if col_lock.button("🔒 Khóa ô", use_container_width=True):
        if selected_slots_to_toggle:
            for s in st.session_state.parking_slots:
                if s["floor"] == selected_floor_admin and s["id"] in selected_slots_to_toggle:
                    s["status"] = "ĐÃ KHÓA"
            st.sidebar.success(f"Đã KHÓA {len(selected_slots_to_toggle)} ô tại {selected_floor_admin}!")
            st.rerun()
            
    if col_unlock.button("🔓 Mở khóa", use_container_width=True):
        if selected_slots_to_toggle:
            for s in st.session_state.parking_slots:
                if s["floor"] == selected_floor_admin and s["id"] in selected_slots_to_toggle:
                    s["status"] = "TRỐNG"
            st.sidebar.success(f"Đã MỞ KHÓA {len(selected_slots_to_toggle)} ô tại {selected_floor_admin}!")
            st.rerun()

    if st.sidebar.button("🔄 Reset toàn bộ bãi đỗ", use_container_width=True):
        for s in st.session_state.parking_slots:
            s["status"] = "TRỐNG"
        st.session_state.last_assigned_slot = None
        st.sidebar.info("Đã đặt lại tất cả các ô về trạng thái TRỐNG!")
        st.rerun()

st.sidebar.markdown("---")

# ==========================================
# 4. THUẬT TOÁN ĐIỀU HÀNH ROBOT AGV & LỰA CHỌN BLOCK
# ==========================================
def find_best_slot_agv(duration, weight, is_priority):
    all_slots = st.session_state.parking_slots
    floors_order = ["Tầng 1", "Tầng B1", "Tầng B2"]
    
    # 1. Tính toán Điểm Ưu tiên Tối ưu (Urgency Score)
    urgency_score = (weight / 1000.0) * 2.5 + (24.0 / (duration + 0.5)) * 3.5
    
    # 2. Quyết định Block mục tiêu ban đầu
    if is_priority or urgency_score >= 12.0:
        target_block = "Block A"  # Gần Cổng AGV nhất
    elif urgency_score >= 8.0:
        target_block = "Block B"
    elif urgency_score >= 4.0:
        target_block = "Block C"
    else:
        target_block = "Block D"  # Sâu nhất

    # 3. Xác định tầng hầm mục tiêu ban đầu
    if is_priority or duration <= 2.0:
        target_floor = "Tầng 1"
    elif duration <= 8.0:
        target_floor = "Tầng B1"
    else:
        target_floor = "Tầng B2"

    start_floor_idx = floors_order.index(target_floor)
    search_floors = floors_order[start_floor_idx:] + floors_order[:start_floor_idx]

    blocks_order = ["Block A", "Block B", "Block C", "Block D"]
    start_block_idx = blocks_order.index(target_block)
    search_blocks = blocks_order[start_block_idx:] + blocks_order[:start_block_idx]

    # DUYỆT QUA CÁC TẦNG VÀ CÁC BLOCK DẠNG MÔ HÌNH XẾP HÌNH
    for current_floor in search_floors:
        for current_block in search_blocks:
            available = [
                s for s in all_slots 
                if s["floor"] == current_floor and s["block"] == current_block and s["status"] == "TRỐNG"
            ]

            if available:
                selected_slot = available[0]
                selected_slot["status"] = "ĐÃ ĐỖ"
                
                # Ước tính năng lượng AGV tiêu thụ (kWh) = Weight * Distance * Factor
                agv_energy = round(weight * selected_slot["distance"] * 0.00012, 2)
                
                return {
                    "slot": selected_slot,
                    "urgency_score": round(urgency_score, 1),
                    "target_block": target_block,
                    "assigned_block": current_block,
                    "agv_energy": agv_energy
                }

    return None

# NÚT KÍCH HOẠT ROBOT AGV TÌM VỊ TRÍ
if st.sidebar.button("🤖 ROBOT AGV VẬN HÀNH ĐỖ XE", use_container_width=True):
    result = find_best_slot_agv(duration, weight, is_priority)
    if result:
        slot = result["slot"]
        st.session_state.last_assigned_slot = result
        st.sidebar.success(f"✅ Robot AGV gán thành công: **{slot['id']}** ({result['assigned_block']} - **{slot['floor']}**)")
    else:
        st.session_state.last_assigned_slot = "FULL"
        st.sidebar.error("⛔ **ROBOT AGV BÁO: BÃI ĐỖ ĐÃ HẾT TẤT CẢ CÁC Ô TRỐNG KHẢ DỤNG!**")

# ==========================================
# 5. HIỂN THỊ TIÊU ĐỀ & THỐNG KÊ TỔNG QUAN
# ==========================================
st.title("🤖 Hệ thống Tối ưu Bãi đỗ xe Tự động (Mô hình Block AGV)")

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
# 6. GIAO DIỆN SƠ ĐỒ SÀN BẢNG BLOCK & CHỈ DẪN HỆ THỐNG
# ==========================================
col_map, col_info = st.columns([3.2, 1])

def render_agv_block_grid(floor_name):
    slots = [s for s in st.session_state.parking_slots if s["floor"] == floor_name]
    last_res = st.session_state.last_assigned_slot
    last_slot_info = last_res["slot"] if isinstance(last_res, dict) else None

    top_rows = [6, 5, 4]
    bottom_rows = [3, 2, 1]

    def build_grid_html(row_list):
        grid_html = '<div style="display: grid; grid-template-columns: repeat(10, 1fr); gap: 6px; margin-bottom: 8px;">'
        for y in row_list:
            for x in range(1, 11):
                slot = next((s for s in slots if s["x"] == x and s["y"] == y), None)
                if not slot:
                    continue
                
                is_last = (last_slot_info and last_slot_info["id"] == slot["id"] and last_slot_info["floor"] == floor_name)
                
                if is_last:
                    bg_color = "#c6f6d5"
                    border_color = "#38a169"
                    text_color = "#22543d"
                    status_text = "AGV 🎯"
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
                    status_text = "⭐ UT"
                else:
                    bg_color = "#ffffff"
                    border_color = "#cbd5e0"
                    text_color = "#2d3748"
                    status_text = slot["block"].replace("Block ", "B-")

                grid_html += f'<div style="background-color: {bg_color}; border: 1.5px solid {border_color}; border-radius: 6px; padding: 5px 1px; text-align: center; font-family: sans-serif;"><div style="font-size: 11px; font-weight: 800; color: {text_color};">{slot["id"]}</div><div style="font-size: 8px; font-weight: 700; color: {text_color}; margin-top: 2px;">{status_text}</div></div>'
        grid_html += '</div>'
        return grid_html

    map_html = f'''<div style="background-color: #ffffff; border-radius: 12px; padding: 18px; border: 1px solid #e2e8f0;">
{build_grid_html(top_rows)}
<div style="display: flex; align-items: center; justify-content: space-between; background-color: #edf2f7; border: 2px dashed #cbd5e0; border-radius: 8px; padding: 8px 14px; margin: 12px 0; font-family: sans-serif;">
<span style="background-color: #fefcbf; color: #744210; border: 1px solid #d69e2e; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">🤖 TRẠM AGV HUB / CỔNG VÀO</span>
<span style="font-size: 11px; font-weight: bold; color: #4a5568; letter-spacing: 1px;">🚗 LÀN ĐƯỜNG DI CHUYỂN AGV (MAIN DRIVEWAY) ──────────────────►</span>
<span style="background-color: #c6f6d5; color: #22543d; border: 1px solid #38a169; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">🚪 LỐI RA</span>
</div>
{build_grid_html(bottom_rows)}
</div>'''

    st.markdown(map_html, unsafe_allow_html=True)

# --- CỘT TRÁI: SƠ ĐỒ BÃI ĐỖ XE ---
with col_map:
    st.subheader("🗺️ Sơ đồ Phân bổ Block bãi đỗ xe")
    
    tab1, tab2, tab3 = st.tabs([
        "Tầng 1 (Cổng AGV & Ngắn hạn)", 
        "Tầng B1 (Trung hạn)", 
        "Tầng B2 (Dài hạn)"
    ])
    
    with tab1:
        render_agv_block_grid("Tầng 1")
    with tab2:
        render_agv_block_grid("Tầng B1")
    with tab3:
        render_agv_block_grid("Tầng B2")

# --- CỘT PHẢI: CHỈ DẪN HỆ THỐNG AGV & THÔNG TIN ---
with col_info:
    st.subheader("📌 Chỉ dẫn Robot AGV")
    
    last_res = st.session_state.last_assigned_slot
    
    if last_res == "FULL":
        st.error("⛔ **THÔNG BÁO AGV:**\n\nHiện tại tất cả các ô trong các Block đều đã **KÍN CHỖ HOẶC BỊ KHÓA**.")
    elif isinstance(last_res, dict):
        s_info = last_res["slot"]
        st.success(f"""
        🎯 **GÁN VỊ TRÍ AGV:** **{s_info['id']}**  
        * **Phân cụm:** `{s_info['block']}`  
        * **Vị trí tầng:** `{s_info['floor']}`  
        * **Tiêu thụ pin AGV dự kiến:** `{last_res['agv_energy']} kWh`
        """)
    else:
        st.info("🎯 **Chưa có lệnh di chuyển cho AGV.**\n\nNhấn nút 'ROBOT AGV VẬN HÀNH ĐỖ XE' để kích hoạt.")

    st.markdown("---")
    st.subheader("ℹ️ Thông tin Khai báo Xe")
    
    st.markdown(f"""
    * **Khối lượng xe:** `{weight} kg`
    * **Thời gian đỗ:** `{duration} giờ`
    * **Đối tượng:** {"⚡ Ưu tiên" if is_priority else "🚗 Thông thường"}
    * **Chỉ số Tối ưu (Urgency):** `{round((weight/1000.0)*2.5 + (24.0/(duration+0.5))*3.5, 1)} điểm`
    """)
    
    st.markdown("---")
    st.caption("**Ghi chú phân vùng Block:**")
    st.caption("🟦 **Block A (B-A)**: Gần Cổng AGV nhất (Tối ưu xe nặng/ngắn hạn)")
    st.caption("🟩 **Block B (B-B)**: Vùng trung bình gần")
    st.caption("🟧 **Block C (B-C)**: Vùng trung bình xa")
    st.caption("🟪 **Block D (B-D)**: Vùng sâu nhất (Tối ưu xe đỗ lâu dài)")
