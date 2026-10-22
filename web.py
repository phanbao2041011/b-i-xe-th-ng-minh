import streamlit as st

# ==========================================
# 1. CẤU HÌNH TRANG WEB
# ==========================================
st.set_page_config(
    page_title="Hệ thống AGV Smart Parking - Sơ đồ 8 Block",
    page_icon="🤖",
    layout="wide"
)

# ==========================================
# 2. KHỞI TẠO BỘ NHỚ 8 BLOCK THEO BẢN VẼ
# ==========================================
if "blocks" not in st.session_state:
    st.session_state.blocks = [
        {"id": "Block 1", "name": "Block 1", "capacity": 10, "occupied": 0, "is_locked": False, "priority_rank": 2, "desc": "Gần Cổng ra (Tối ưu đỗ cực ngắn hạn)"},
        {"id": "Block 2", "name": "Block 2", "capacity": 10, "occupied": 0, "is_locked": False, "priority_rank": 3, "desc": "Khu vực trung tâm dưới (Trung hạn)"},
        {"id": "Block 3", "name": "Block 3", "capacity": 10, "occupied": 0, "is_locked": False, "priority_rank": 2, "desc": "Khu vực trung tâm dưới (Gần cổng vào)"},
        {"id": "Block 4", "name": "Block 4", "capacity": 10, "occupied": 0, "is_locked": False, "priority_rank": 1, "desc": "Sát Cổng vào (Ưu tiên xe nặng/vừa vào)"},
        {"id": "Block 5", "name": "Block 5", "capacity": 15, "occupied": 0, "is_locked": False, "priority_rank": 4, "desc": "Khối ngang giữa (Trung hạn)"},
        {"id": "Block 6", "name": "Block 6", "capacity": 15, "occupied": 0, "is_locked": False, "priority_rank": 5, "desc": "Khối ngang trên cùng (Sâu nhất - Dài hạn)"},
        {"id": "Block 7", "name": "Block 7", "capacity": 10, "occupied": 0, "is_locked": False, "priority_rank": 1, "desc": "Khối dọc bên phải (Cổng vào)"},
        {"id": "Block 8", "name": "Block 8", "capacity": 10, "occupied": 0, "is_locked": False, "priority_rank": 3, "desc": "Khối dọc bên trái (Lối ra)"},
    ]

if "last_assigned_res" not in st.session_state:
    st.session_state.last_assigned_res = None

# ==========================================
# 3. THANH BÊN (SIDEBAR) - KHAI BÁO THÔNG TIN
# ==========================================
st.sidebar.header("📋 Khai báo Xe vào Cổng")

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
    
    block_options = [f"Block {i}" for i in range(1, 9)]
    selected_block_ids = st.sidebar.multiselect(
        "Chọn Block cần thao tác:",
        options=block_options,
        placeholder="Chọn một hoặc nhiều Block..."
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
# 4. THUẬT TOÁN AGV LỰA CHỌN BLOCK TỐI ƯU
# ==========================================
def assign_agv_block(weight, duration, is_priority):
    blocks = st.session_state.blocks
    
    # 1. Tính toán Chỉ số Tối ưu (Urgency Score)
    urgency_score = (weight / 1000.0) * 2.5 + (24.0 / (duration + 0.5)) * 3.5
    
    # 2. Xếp thứ tự ưu tiên các Block dựa trên tham số đầu vào
    if is_priority or urgency_score >= 12.0:
        # Xe rất nặng hoặc siêu ngắn hạn -> Ưu tiên Block 4, 7 (gần Cổng vào) hoặc Block 1 (gần Cổng ra)
        preferred_order = ["Block 4", "Block 7", "Block 1", "Block 3", "Block 2", "Block 5", "Block 8", "Block 6"]
    elif urgency_score >= 7.0:
        preferred_order = ["Block 3", "Block 2", "Block 1", "Block 5", "Block 7", "Block 4", "Block 8", "Block 6"]
    else:
        # Đỗ lâu dài / Xe nhẹ -> Ưu tiên các khối nằm sâu như Block 6, 5, 8
        preferred_order = ["Block 6", "Block 5", "Block 8", "Block 2", "Block 3", "Block 7", "Block 1", "Block 4"]

    # DUYỆT TÌM BLOCK CÒN CHỖ VÀ KHÔNG BỊ KHÓA
    for b_id in preferred_order:
        blk = next((b for b in blocks if b["id"] == b_id), None)
        if blk and (not blk["is_locked"]) and (blk["occupied"] < blk["capacity"]):
            blk["occupied"] += 1
            agv_energy = round(weight * blk["priority_rank"] * 0.00015, 2)
            
            return {
                "assigned_block": blk,
                "urgency_score": round(urgency_score, 1),
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
st.title("🤖 Hệ thống Tối ưu Bãi đỗ xe Tự động (Mô hình 8 Block AGV)")

total_capacity = sum(b["capacity"] for b in st.session_state.blocks)
total_occupied = sum(b["occupied"] for b in st.session_state.blocks)
total_free = total_capacity - total_occupied
locked_blocks_count = sum(1 for b in st.session_state.blocks if b["is_locked"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Tổng quy mô bãi", f"{total_capacity} xe")
col2.metric("Số chỗ còn trống", f"{total_free} chỗ")
col3.metric("Số xe đã đỗ", f"{total_occupied} xe")
col4.metric("Số Block tạm khóa", f"{locked_blocks_count} / 8")

st.divider()

# ==========================================
# 6. MÔ PHỎNG CHÍNH XÁC SƠ ĐỒ 8 BLOCK THEO BẢN VẼ
# ==========================================
col_map, col_info = st.columns([3.3, 1])

def get_block_dict():
    return {b["id"]: b for b in st.session_state.blocks}

def render_block_card_html(b, is_vertical=False):
    last_res = st.session_state.last_assigned_res
    last_b_id = last_res["assigned_block"]["id"] if isinstance(last_res, dict) else None
    
    is_assigned = (last_b_id == b["id"])
    pct = int((b["occupied"] / b["capacity"]) * 100)

    if b["is_locked"]:
        status_tag = '<span style="background-color: #cbd5e0; color: #2d3748; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;">🔒 KHÓA</span>'
        border = "2px solid #a0aec0"
        bg = "#f7fafc"
    elif is_assigned:
        status_tag = '<span style="background-color: #38a169; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;">🎯 CHỌN</span>'
        border = "3px solid #38a169"
        bg = "#f0fff4"
    elif b["occupied"] >= b["capacity"]:
        status_tag = '<span style="background-color: #e53e3e; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;">🔴 ĐẦY</span>'
        border = "2px solid #e53e3e"
        bg = "#fff5f5"
    else:
        status_tag = '<span style="background-color: #3182ce; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;">🟢 TRỐNG</span>'
        border = "2px solid #cbd5e0"
        bg = "#ffffff"

    height_style = "height: 100%; min-height: 380px; display: flex; flex-direction: column; justify-content: center;" if is_vertical else ""

    return f'''
    <div style="{height_style} background-color: {bg}; border: {border}; border-radius: 8px; padding: 12px; text-align: center; font-family: sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.04);">
        <div style="font-size: 15px; font-weight: 800; color: #2d3748; margin-bottom: 4px;">{b["name"]}</div>
        <div style="margin-bottom: 6px;">{status_tag}</div>
        <div style="font-size: 12px; font-weight: 700; color: #4a5568; margin-bottom: 4px;">{b["occupied"]} / {b["capacity"]} xe</div>
        <div style="background-color: #e2e8f0; border-radius: 4px; height: 8px; width: 100%; overflow: hidden; margin-bottom: 6px;">
            <div style="background-color: {"#e53e3e" if pct==100 else "#3182ce"}; width: {pct}%; height: 100%;"></div>
        </div>
        <div style="font-size: 10px; color: #718096; line-height: 1.2;">{b["desc"]}</div>
    </div>
    '''

def render_exact_grid():
    bd = get_block_dict()

    grid_layout_html = f'''
    <div style="background-color: #f8fafc; border-radius: 12px; padding: 16px; border: 1.5px solid #cbd5e0;">
        <div style="display: grid; grid-template-columns: 120px 1fr 120px; gap: 14px; align-items: stretch;">
            
            <!-- CỘT TRÁI: BLOCK 8 -->
            <div>
                {render_block_card_html(bd["Block 8"], is_vertical=True)}
            </div>

            <!-- CỘT GIỮA: BLOCK 6, BLOCK 5, VÀ BLOCK 1-4 -->
            <div style="display: flex; flex-direction: column; gap: 12px;">
                <!-- BLOCK 6 (HÀNG TRÊN) -->
                <div>{render_block_card_html(bd["Block 6"])}</div>

                <!-- BLOCK 5 (HÀNG GIỮA) -->
                <div>{render_block_card_html(bd["Block 5"])}</div>

                <!-- KHỐI 1, 2, 3, 4 (HÀNG DƯỚI) -->
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;">
                    <div>{render_block_card_html(bd["Block 1"])}</div>
                    <div>{render_block_card_html(bd["Block 2"])}</div>
                    <div>{render_block_card_html(bd["Block 3"])}</div>
                    <div>{render_block_card_html(bd["Block 4"])}</div>
                </div>

                <!-- CỔNG RA VÀ CỔNG VÀO -->
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background-color: #edf2f7; border-radius: 6px; border: 1px dashed #cbd5e0; margin-top: 4px;">
                    <span style="background-color: #fed7d7; color: #9b2c2c; border: 1px solid #e53e3e; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: bold;">
                        🚪 CỔNG RA
                    </span>
                    <span style="font-size: 11px; font-weight: bold; color: #718096; letter-spacing: 1px;">
                        🚗 HƯỚNG DI CHUYỂN ROBOT AGV
                    </span>
                    <span style="background-color: #c6f6d5; color: #22543d; border: 1px solid #38a169; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: bold;">
                        🚪 CỔNG VÀO
                    </span>
                </div>
            </div>

            <!-- CỘT PHẢI: BLOCK 7 -->
            <div>
                {render_block_card_html(bd["Block 7"], is_vertical=True)}
            </div>
            
        </div>
    </div>
    '''
    st.markdown(grid_layout_html, unsafe_allow_html=True)

# --- CỘT TRÁI: SƠ ĐỒ MẶT BẰNG 8 BLOCK ---
with col_map:
    st.subheader("🗺️ Sơ đồ Mặt bằng 8 Block đỗ xe")
    render_exact_grid()

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
        ### **{assigned_b['name']}**
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
    st.caption("**Quy tắc phân vùng sơ đồ:**")
    st.caption("🔹 **Block 4, 7**: Gần Cổng vào (Ưu tiên xe nặng/vừa vào)")
    st.caption("🔹 **Block 1**: Gần Cổng ra (Ưu tiên xe cực ngắn hạn)")
    st.caption("🔹 **Block 2, 3, 5, 8**: Khu vực trung tâm bãi")
    st.caption("🔹 **Block 6**: Vùng sâu nhất (Tối ưu đỗ dài hạn)")
