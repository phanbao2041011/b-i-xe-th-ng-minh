import streamlit as st

# ==========================================
# 1. CẤU HÌNH TRANG WEB
# ==========================================
st.set_page_config(
    page_title="Hệ thống AGV Smart Parking - Quản lý Block",
    page_icon="🤖",
    layout="wide"
)

# ==========================================
# 2. KHỞI TẠO BỘ NHỚ CÁC BLOCK ĐỖ XE
# ==========================================
if "blocks" not in st.session_state:
    st.session_state.blocks = [
        {
            "id": "Block A",
            "name": "BLOCK A (Sát Cổng AGV)",
            "capacity": 15,
            "occupied": 0,
            "is_locked": False,
            "distance": 1,
            "color": "#ebf8ff",
            "border_color": "#3182ce",
            "desc": "Ưu tiên: Xe trọng lượng lớn / Đỗ rất ngắn hạn"
        },
        {
            "id": "Block B",
            "name": "BLOCK B (Khu vực Phía Trên)",
            "capacity": 15,
            "occupied": 0,
            "is_locked": False,
            "distance": 2,
            "color": "#f0fff4",
            "border_color": "#38a169",
            "desc": "Ưu tiên: Xe tải trọng trung bình / Đỗ ngắn hạn"
        },
        {
            "id": "Block C",
            "name": "BLOCK C (Khu vực Phía Dưới)",
            "capacity": 15,
            "occupied": 0,
            "is_locked": False,
            "distance": 3,
            "color": "#fffaf0",
            "border_color": "#dd6b20",
            "desc": "Ưu tiên: Xe đỗ trung hạn"
        },
        {
            "id": "Block D",
            "name": "BLOCK D (Khu vực Góc Sâu)",
            "capacity": 15,
            "occupied": 0,
            "is_locked": False,
            "distance": 4,
            "color": "#faf5ff",
            "border_color": "#805ad5",
            "desc": "Ưu tiên: Xe đỗ dài hạn / Xe nhẹ"
        }
    ]

if "last_assigned_res" not in st.session_state:
    st.session_state.last_assigned_res = None

# ==========================================
# 3. THANH BÊN (SIDEBAR) - KHAI BÁO THÔNG TIN
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
    help="Robot AGV sẽ tính toán năng lượng tiêu thụ dựa trên khối lượng xe."
)

# --- CHẾ ĐỘ QUẢN TRỊ VIÊN (ADMIN MODE) ---
st.sidebar.markdown("---")
admin_mode = st.sidebar.checkbox("🛡️ Chế độ Quản trị viên (Admin)")

if admin_mode:
    st.sidebar.subheader("⚙️ Quản lý Khóa / Mở Block")
    
    selected_block_ids = st.sidebar.multiselect(
        "Chọn Block cần thao tác:",
        options=["Block A", "Block B", "Block C", "Block D"],
        placeholder="Chọn Block..."
    )
    
    col_lock, col_unlock = st.sidebar.columns(2)
    
    if col_lock.button("🔒 Khóa Block", use_container_width=True):
        if selected_block_ids:
            for b in st.session_state.blocks:
                if b["id"] in selected_block_ids:
                    b["is_locked"] = True
            st.sidebar.success(f"Đã KHÓA các block: {', '.join(selected_block_ids)}")
            st.rerun()
            
    if col_unlock.button("🔓 Mở Block", use_container_width=True):
        if selected_block_ids:
            for b in st.session_state.blocks:
                if b["id"] in selected_block_ids:
                    b["is_locked"] = False
            st.sidebar.success(f"Đã MỞ KHÓA các block: {', '.join(selected_block_ids)}")
            st.rerun()

    if st.sidebar.button("🔄 Reset toàn bộ bãi đỗ", use_container_width=True):
        for b in st.session_state.blocks:
            b["occupied"] = 0
            b["is_locked"] = False
        st.session_state.last_assigned_res = None
        st.sidebar.info("Đã khôi phục tất cả các Block về trạng thái trống!")
        st.rerun()

st.sidebar.markdown("---")

# ==========================================
# 4. THUẬT TOÁN ĐIỀU HÀNH AGV PHÂN BỔ BLOCK
# ==========================================
def assign_agv_block(weight, duration, is_priority):
    blocks = st.session_state.blocks
    
    # 1. Tính toán Chỉ số Cần thiết Tối ưu (Urgency Score)
    urgency_score = (weight / 1000.0) * 2.5 + (24.0 / (duration + 0.5)) * 3.5
    
    # 2. Xác định Block mục tiêu lý tưởng
    if is_priority or urgency_score >= 12.0:
        target_id = "Block A"
    elif urgency_score >= 8.0:
        target_id = "Block B"
    elif urgency_score >= 4.0:
        target_id = "Block C"
    else:
        target_id = "Block D"

    # Thứ tự tìm kiếm ưu tiên: Block mục tiêu -> Các Block lân cận
    blocks_order = ["Block A", "Block B", "Block C", "Block D"]
    start_idx = blocks_order.index(target_id)
    search_order = blocks_order[start_idx:] + blocks_order[:start_idx]

    # DUYỆT TÌM BLOCK CÒN CHỖ VÀ KHÔNG BỊ KHÓA
    for b_id in search_order:
        blk = next((b for b in blocks if b["id"] == b_id), None)
        if blk and (not blk["is_locked"]) and (blk["occupied"] < blk["capacity"]):
            # Cộng thêm 1 xe vào Block này
            blk["occupied"] += 1
            
            # Ước tính năng lượng AGV tiêu thụ
            agv_energy = round(weight * blk["distance"] * 0.00012, 2)
            
            return {
                "assigned_block": blk,
                "urgency_score": round(urgency_score, 1),
                "target_id": target_id,
                "agv_energy": agv_energy
            }

    return None

# NÚT KÍCH HOẠT VẬN HÀNH AGV
if st.sidebar.button("🤖 ROBOT AGV VẬN HÀNH ĐỖ XE", use_container_width=True):
    res = assign_agv_block(weight, duration, is_priority)
    if res:
        st.session_state.last_assigned_res = res
        assigned_b = res["assigned_block"]
        st.sidebar.success(f"✅ AGV đã chọn: **{assigned_b['id']}** ({assigned_b['occupied']}/{assigned_b['capacity']} xe)")
    else:
        st.session_state.last_assigned_res = "FULL"
        st.sidebar.error("⛔ **ROBOT AGV BÁO: TẤT CẢ CÁC BLOCK ĐẦY HOẶC BỊ KHÓA!**")

# ==========================================
# 5. HIỂN THỊ TIÊU ĐỀ & THỐNG KÊ TỔNG QUAN
# ==========================================
st.title("🤖 Hệ thống Tối ưu Bãi đỗ xe Tự động (Mô hình Khối Block)")

total_capacity = sum(b["capacity"] for b in st.session_state.blocks)
total_occupied = sum(b["occupied"] for b in st.session_state.blocks)
total_free = total_capacity - total_occupied
locked_blocks_count = sum(1 for b in st.session_state.blocks if b["is_locked"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Tổng quy mô bãi", f"{total_capacity} xe")
col2.metric("Số chỗ còn trống", f"{total_free} chỗ")
col3.metric("Số xe đã đỗ", f"{total_occupied} xe")
col4.metric("Số Block tạm khóa", f"{locked_blocks_count} / 4")

st.divider()

# ==========================================
# 6. GIAO DIỆN SƠ ĐỒ MẶT BẰNG DẠNG KHỐI BLOCK
# ==========================================
col_map, col_info = st.columns([3.2, 1])

def render_block_cards():
    blocks = st.session_state.blocks
    last_res = st.session_state.last_assigned_res
    last_b_id = last_res["assigned_block"]["id"] if isinstance(last_res, dict) else None

    def get_card_html(b):
        is_assigned = (last_b_id == b["id"])
        
        # Màu sắc & trạng thái
        if b["is_locked"]:
            status_tag = '<span style="background-color: #cbd5e0; color: #2d3748; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">🔒 ĐÃ KHÓA</span>'
            border = "2px solid #a0aec0"
            bg = "#f7fafc"
        elif is_assigned:
            status_tag = '<span style="background-color: #38a169; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">🎯 AGV VỪA GÁN</span>'
            border = "3px solid #38a169"
            bg = "#f0fff4"
        elif b["occupied"] >= b["capacity"]:
            status_tag = '<span style="background-color: #e53e3e; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">🔴 ĐÃ ĐẦY</span>'
            border = "2px solid #e53e3e"
            bg = "#fff5f5"
        else:
            status_tag = '<span style="background-color: #3182ce; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">🟢 CÒN CHỖ</span>'
            border = f"2px solid {b['border_color']}"
            bg = b["color"]

        pct = int((b["occupied"] / b["capacity"]) * 100)

        card_html = f'''<div style="background-color: {bg}; border: {border}; border-radius: 10px; padding: 16px; margin-bottom: 12px; font-family: sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
    <span style="font-size: 16px; font-weight: 800; color: #2d3748;">{b["name"]}</span>
    {status_tag}
</div>
<div style="font-size: 13px; color: #4a5568; margin-bottom: 8px;"><b>Sức chứa:</b> {b["occupied"]} / {b["capacity"]} xe ({pct}%)</div>
<div style="background-color: #e2e8f0; border-radius: 6px; height: 10px; width: 100%; overflow: hidden; margin-bottom: 8px;">
    <div style="background-color: {"#e53e3e" if pct==100 else "#3182ce"}; width: {pct}%; height: 100%;"></div>
</div>
<div style="font-size: 11px; color: #718096;"><i>{b["desc"]}</i></div>
</div>'''
        return card_html

    b_a = next(b for b in blocks if b["id"] == "Block A")
    b_b = next(b for b in blocks if b["id"] == "Block B")
    b_c = next(b for b in blocks if b["id"] == "Block C")
    b_d = next(b for b in blocks if b["id"] == "Block D")

    grid_html = f'''<div style="background-color: #ffffff; border-radius: 12px; padding: 20px; border: 1px solid #e2e8f0;">
<!-- KHỐI PHÍA TRÊN -->
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
    {get_card_html(b_a)}
    {get_card_html(b_b)}
</div>

<!-- LÀN ĐƯỜNG AGV -->
<div style="display: flex; align-items: center; justify-content: space-between; background-color: #edf2f7; border: 2px dashed #cbd5e0; border-radius: 8px; padding: 10px 16px; margin: 12px 0; font-family: sans-serif;">
    <span style="background-color: #fefcbf; color: #744210; border: 1px solid #d69e2e; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">🤖 TRẠM AGV HUB / CỔNG VÀO</span>
    <span style="font-size: 12px; font-weight: bold; color: #4a5568; letter-spacing: 1px;">🚗 LÀN ĐƯỜNG VẬN CHUYỂN CỦA ROBOT AGV ──────────────────►</span>
    <span style="background-color: #c6f6d5; color: #22543d; border: 1px solid #38a169; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">🚪 LỐI RA</span>
</div>

<!-- KHỐI PHÍA DƯỚI -->
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
    {get_card_html(b_c)}
    {get_card_html(b_d)}
</div>
</div>'''

    st.markdown(grid_html, unsafe_allow_html=True)

# --- CỘT TRÁI: SƠ ĐỒ KHỐI BLOCK ---
with col_map:
    st.subheader("🗺️ Sơ đồ Mặt bằng các Khối đỗ xe (Block Model)")
    render_block_cards()

# --- CỘT PHẢI: CHỈ DẪN ROBOT AGV & THÔNG TIN ---
with col_info:
    st.subheader("📌 Chỉ dẫn Robot AGV")
    
    last_res = st.session_state.last_assigned_res
    
    if last_res == "FULL":
        st.error("⛔ **THÔNG BÁO AGV:**\n\nTất cả các Block đều đã **KÍN CHỖ HOẶC BỊ KHÓA**.")
    elif isinstance(last_res, dict):
        assigned_b = last_res["assigned_block"]
        st.success(f"""
        🎯 **GÁN VẬN CHUYỂN ĐẾN:**
        ### **{assigned_b['id']}**
        * **Sức chứa hiện tại:** `{assigned_b['occupied']} / {assigned_b['capacity']} xe`
        * **Tiêu thụ pin AGV dự kiến:** `{last_res['agv_energy']} kWh`
        """)
    else:
        st.info("🎯 **Chưa có lệnh vận chuyển.**\n\nNhấn nút 'ROBOT AGV VẬN HÀNH ĐỖ XE' ở thanh bên để gán khối đỗ.")

    st.markdown("---")
    st.subheader("ℹ️ Thông tin Khai báo Xe")
    
    st.markdown(f"""
    * **Khối lượng xe:** `{weight} kg`
    * **Thời gian đỗ:** `{duration} giờ`
    * **Đối tượng:** {"⚡ Ưu tiên" if is_priority else "🚗 Thông thường"}
    * **Điểm Tối ưu (Urgency):** `{round((weight/1000.0)*2.5 + (24.0/(duration+0.5))*3.5, 1)} điểm`
    """)
    
    st.markdown("---")
    st.caption("**Quy tắc phân vùng Block:**")
    st.caption("🟦 **Block A**: Sát Cổng AGV (D=1)")
    st.caption("🟩 **Block B**: Phía trên đường chính (D=2)")
    st.caption("🟧 **Block C**: Phía dưới đường chính (D=3)")
    st.caption("🟪 **Block D**: Góc sâu nhất (D=4)")
