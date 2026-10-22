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
# ==========================================
# 6. MÔ PHỎNG SƠ ĐỒ 8 BLOCK VỚI CÁC LỐI ĐI ROBOT AGV (ĐÃ NÂNG CẤP KO BỊ DÍNH SÁT)
# ==========================================
col_map, col_info = st.columns([3.3, 1])

def get_block_dict():
    return {b["id"]: b for b in st.session_state.blocks}

def render_block_card_html(b, is_vertical=False):
    last_res = st.session_state.last_assigned_res
    last_b_id = last_res["assigned_block"]["id"] if isinstance(last_res, dict) else None
    
    is_assigned = (last_b_id == b["id"])
    pct = int((b["occupied"] / b["capacity"]) * 100)

    # ĐỊNH DẠNG TẠO HIỆU ỨNG KHỐI TÒA NHÀ 3D (BUILDING BLOCK STYLING)
    if b["is_locked"]:
        status_tag = '<span style="background-color: #475569; color: #ffffff; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;">🔒 KHÓA</span>'
        bg_gradient = "linear-gradient(145deg, #cbd5e1, #94a3b8)"
        border_style = "2px solid #64748b"
        shadow_style = "box-shadow: 0 4px 6px rgba(0,0,0,0.1), inset 0 2px 0 rgba(255,255,255,0.5), 0 5px 0 #475569;"
        text_color = "#1e293b"
    elif is_assigned:
        status_tag = '<span style="background-color: #15803d; color: #ffffff; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">🎯 AGV CHỌN</span>'
        bg_gradient = "linear-gradient(145deg, #dcfce7, #86efac)"
        border_style = "2.5px solid #16a34a"
        shadow_style = "box-shadow: 0 0 15px rgba(34, 197, 94, 0.4), inset 0 2px 0 rgba(255,255,255,0.7), 0 6px 0 #15803d;"
        text_color = "#064e3b"
    elif b["occupied"] >= b["capacity"]:
        status_tag = '<span style="background-color: #b91c1c; color: #ffffff; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;">🔴 ĐÃ ĐẦY</span>'
        bg_gradient = "linear-gradient(145deg, #ffe4e6, #fca5a5)"
        border_style = "2px solid #ef4444"
        shadow_style = "box-shadow: 0 4px 6px rgba(0,0,0,0.1), inset 0 2px 0 rgba(255,255,255,0.5), 0 5px 0 #991b1b;"
        text_color = "#881337"
    else:
        status_tag = '<span style="background-color: #2563eb; color: #ffffff; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;">🟢 TRỐNG</span>'
        bg_gradient = "linear-gradient(145deg, #ffffff, #f1f5f9)"
        border_style = "2px solid #cbd5e1"
        shadow_style = "box-shadow: 0 4px 8px rgba(0,0,0,0.06), inset 0 2px 0 rgba(255,255,255,0.9), 0 5px 0 #94a3b8;"
        text_color = "#0f172a"

    height_style = "height: 100%; min-height: 420px; display: flex; flex-direction: column; justify-content: center;" if is_vertical else ""

    return f'<div style="{height_style} background: {bg_gradient}; border: {border_style}; border-radius: 12px; padding: 16px 10px; text-align: center; font-family: system-ui, -apple-system, sans-serif; {shadow_style}"><div style="font-size: 16px; font-weight: 800; color: {text_color}; margin-bottom: 6px; letter-spacing: 0.5px;">🏢 {b["name"]}</div><div style="margin-bottom: 8px;">{status_tag}</div><div style="font-size: 13px; font-weight: 700; color: {text_color}; margin-bottom: 8px;">{b["occupied"]} / {b["capacity"]} xe</div><div style="background-color: rgba(0,0,0,0.08); border-radius: 6px; height: 10px; width: 100%; overflow: hidden; border: 1px solid rgba(0,0,0,0.05);"><div style="background: {"linear-gradient(90deg, #f43f5e, #be123c)" if pct==100 else "linear-gradient(90deg, #3b82f6, #1d4ed8)"}; width: {pct}%; height: 100%; border-radius: 6px;"></div></div></div>'

def render_exact_grid():
    bd = get_block_dict()

    grid_layout_html = f'''<div style="background-color: #f8fafc; border-radius: 16px; padding: 20px; border: 2px solid #cbd5e1; box-shadow: inset 0 0 15px rgba(0,0,0,0.02);">
<div style="display: grid; grid-template-columns: 125px 28px 1fr 28px 125px; gap: 8px; align-items: stretch;">

<!-- CỘT 1: BLOCK 8 -->
<div>{render_block_card_html(bd["Block 8"], is_vertical=True)}</div>

<!-- CỘT 2: LỐI ĐI AGV DỌC TRÁI -->
<div style="background-color: #e2e8f0; border: 1.5px dashed #94a3b8; border-radius: 8px; display: flex; align-items: center; justify-content: center; writing-mode: vertical-rl; font-size: 11px; font-weight: bold; color: #64748b; letter-spacing: 2px; padding: 4px;">
↕ LỐI ĐI AGV DỌC TRÁI
</div>

<!-- CỘT 3: KHU VỰC TRUNG TÂM -->
<div style="display: flex; flex-direction: column; gap: 10px;">
<div>{render_block_card_html(bd["Block 6"])}</div>

<!-- LÀN AGV NGANG 1 -->
<div style="background-color: #edf2f7; border: 1.5px dashed #cbd5e0; border-radius: 6px; padding: 4px 10px; text-align: center; font-size: 11px; font-weight: bold; color: #64748b; letter-spacing: 1px;">
↔ LÀN DI CHUYỂN AGV (HÀNG NGANG 1)
</div>

<div>{render_block_card_html(bd["Block 5"])}</div>

<!-- LÀN AGV NGANG 2 -->
<div style="background-color: #edf2f7; border: 1.5px dashed #cbd5e0; border-radius: 6px; padding: 4px 10px; text-align: center; font-size: 11px; font-weight: bold; color: #64748b; letter-spacing: 1px;">
↔ LÀN DI CHUYỂN AGV (HÀNG NGANG 2)
</div>

<!-- KHỐI 1, 2, 3, 4 CÓ KHOẢNG CÁCH RỘNG -->
<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px;">
<div>{render_block_card_html(bd["Block 1"])}</div>
<div>{render_block_card_html(bd["Block 2"])}</div>
<div>{render_block_card_html(bd["Block 3"])}</div>
<div>{render_block_card_html(bd["Block 4"])}</div>
</div>

<!-- CỔNG RA VÀ CỔNG VÀO -->
<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 14px; background-color: #edf2f7; border-radius: 8px; border: 2px dashed #cbd5e0; margin-top: 4px;">
<span style="background-color: #fed7d7; color: #9b2c2c; border: 1.5px solid #e53e3e; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: bold;">🚪 CỔNG RA</span>
<span style="font-size: 12px; font-weight: bold; color: #64748b; letter-spacing: 1.5px;">🚗 HƯỚNG RA / VÀO ROBOT AGV</span>
<span style="background-color: #c6f6d5; color: #22543d; border: 1.5px solid #38a169; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: bold;">🚪 CỔNG VÀO</span>
</div>
</div>

<!-- CỘT 4: LỐI ĐI AGV DỌC PHẢI -->
<div style="background-color: #e2e8f0; border: 1.5px dashed #94a3b8; border-radius: 8px; display: flex; align-items: center; justify-content: center; writing-mode: vertical-rl; font-size: 11px; font-weight: bold; color: #64748b; letter-spacing: 2px; padding: 4px;">
↕ LỐI ĐI AGV DỌC PHẢI
</div>

<!-- CỘT 5: BLOCK 7 -->
<div>{render_block_card_html(bd["Block 7"], is_vertical=True)}</div>
</div>
</div>'''

    st.markdown(grid_layout_html, unsafe_allow_html=True)

# --- CỘT TRÁI: SƠ ĐỒ MẶT BẰNG 8 BLOCK ---
with col_map:
    st.subheader("🗺️ Sơ đồ Mặt bằng 8 Block & Luồng xe Robot AGV")
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
    st.caption("**Chú thích trạng thái:**")
    st.caption("🟢 **TRỐNG**: Khối đỗ còn chỗ")
    st.caption("🔴 **ĐÃ ĐẦY**: Khối đỗ đã kín xe")
    st.caption("🔒 **KHÓA**: Khối đỗ tạm khóa")
    st.caption("🎯 **AGV CHỌN**: Khối đỗ vừa được gán")

