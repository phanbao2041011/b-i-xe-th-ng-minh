import streamlit as st
import math

# ==========================================
# 1. CẤU HÌNH TRANG WEB STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Hệ thống Tối ưu Bãi đỗ xe Tự động AGV",
    page_icon="🤖",
    layout="wide"
)

# ==========================================
# 2. KHỞI TẠO VÀ ĐỒNG BỘ SESSION STATE (9 BLOCK)
# ==========================================
if "blocks" not in st.session_state or len(st.session_state.blocks) != 9:
    st.session_state.blocks = [
        {"id": f"Block {i}", "name": f"Block {i}", "capacity": 12, "occupied": 0, "is_locked": False}
        for i in range(1, 10)
    ]

# Ép đồng bộ sức chứa 12 xe cho tất cả 9 Block
for b in st.session_state.blocks:
    b["capacity"] = 12

if "last_assigned_res" not in st.session_state:
    st.session_state.last_assigned_res = None


# ==========================================
# 3. THUẬT TOÁN TÍNH TOÁN & TỐI ƯU HÓA AGV
# ==========================================
# Bảng khoảng cách cơ sở từ Cổng vào (ENTRY) đến tâm từng Block (đơn vị: bước lưới)
BLOCK_DISTANCES = {
    "Block 1": 4, "Block 2": 3, "Block 3": 2, "Block 4": 1,
    "Block 5": 5, "Block 6": 7, "Block 7": 2, "Block 8": 8, "Block 9": 6
}

def calculate_urgency(weight, duration, is_priority):
    """Tính điểm cấp thiết / ưu tiên đỗ xe"""
    score = (weight / 1000.0) * 2.5 + (24.0 / (duration + 0.5)) * 3.5
    if is_priority:
        score += 5.0
    return round(score, 2)

def calculate_agv_energy(block_id, weight):
    """Tính toán mức tiêu thụ năng lượng của Robot AGV (kWh)"""
    dist = BLOCK_DISTANCES.get(block_id, 5)
    e_base = 0.03   # Năng lượng cơ sở khi AGV di chuyển không tải
    k_load = 0.000025  # Hệ số phụ thuộc tải trọng xe
    energy = dist * (e_base + k_load * weight)
    return round(energy, 2)

def find_optimal_block(weight, duration, is_priority):
    """Thuật toán sàng lọc và lựa chọn Block tối ưu"""
    urgency = calculate_urgency(weight, duration, is_priority)
    
    # 1. Lọc các Block hợp lệ (chưa khóa và còn chỗ trống)
    valid_blocks = [b for b in st.session_state.blocks if not b["is_locked"] and b["occupied"] < b["capacity"]]
    
    if not valid_blocks:
        return "FULL"

    best_block = None
    min_cost = float('inf')

    # Trọng số tối ưu hóa (w1: Năng lượng AGV, w2: Phù hợp phân vùng)
    w1, w2 = 0.6, 0.4

    for b in valid_blocks:
        b_id = b["id"]
        energy = calculate_agv_energy(b_id, weight)
        
        # Điểm lý tưởng chiến lược từng vùng
        ideal_score = 15.0
        if b_id in ["Block 4", "Block 7"]:
            ideal_score = 25.0  # Ưu tiên xe nặng/cấp thiết gần cổng vào
        elif b_id in ["Block 1", "Block 9"]:
            ideal_score = 20.0  # Gần cổng ra
        elif b_id in ["Block 5", "Block 6"]:
            ideal_score = 8.0   # Đỗ dài hạn vùng sâu

        # Hàm chi phí tổng hợp
        occupancy_ratio = b["occupied"] / b["capacity"]
        penalty = occupancy_ratio * 3.0  # Phạt nhẹ nếu block đã gần đầy để cân bằng tải
        
        cost = w1 * energy * 10 + w2 * abs(urgency - ideal_score) + penalty

        if cost < min_cost:
            min_cost = cost
            best_block = b

    energy_used = calculate_agv_energy(best_block["id"], weight)
    return {
        "assigned_block": best_block,
        "agv_energy": energy_used,
        "urgency_score": urgency
    }


# ==========================================
# 4. THANH BÊN (SIDEBAR) - KHAI BÁO & QUẢN TRỊ
# ==========================================
st.sidebar.title("🎮 Điều hành & Khai báo")

st.sidebar.subheader("📋 Khai báo Xe vào Cổng")
is_priority = st.sidebar.checkbox("⚡ Đối tượng Ưu tiên", value=False)
duration = st.sidebar.number_input("⏱️ Thời gian đỗ dự kiến (giờ):", min_value=0.5, max_value=72.0, value=2.0, step=0.5)
weight = st.sidebar.number_input("⚖️ Khối lượng xe (kg):", min_value=500, max_value=3500, value=1500, step=50)

st.sidebar.markdown("---")

# Nut vận hành AGV
if st.sidebar.button("🚗 ROBOT AGV VẬN HÀNH ĐỖ XE", type="primary", use_container_width=True):
    res = find_optimal_block(weight, duration, is_priority)
    st.session_state.last_assigned_res = res
    if res != "FULL" and isinstance(res, dict):
        # Tăng số lượng xe trong Block được chọn
        target_id = res["assigned_block"]["id"]
        for b in st.session_state.blocks:
            if b["id"] == target_id:
                b["occupied"] += 1
                break
        st.sidebar.success(f"✅ Robot AGV đã vận chuyển xe vào **{target_id}**!")
    else:
        st.sidebar.error("❌ Tất cả các Block đều đã KÍN CHỖ hoặc BỊ KHÓA!")

st.sidebar.markdown("---")

# Chế độ Admin
st.sidebar.subheader("⚙️ Chế độ Quản trị viên (Admin)")
admin_mode = st.sidebar.checkbox("🔓 Bật Chế độ Quản trị", value=True)

if admin_mode:
    st.sidebar.caption("🔒 **Quản lý Khóa / Mở Block:**")
    selected_to_lock = st.sidebar.multiselect(
        "Chọn Block muốn Khóa:",
        options=[b["id"] for b in st.session_state.blocks],
        default=[b["id"] for b in st.session_state.blocks if b["is_locked"]]
    )
    
    # Cập nhật trạng thái khóa
    for b in st.session_state.blocks:
        b["is_locked"] = (b["id"] in selected_to_lock)

    if st.sidebar.button("🔄 Đặt lại Trạng thái Bãi đỗ (Reset)", use_container_width=True):
        for b in st.session_state.blocks:
            b["occupied"] = 0
            b["is_locked"] = False
        st.session_state.last_assigned_res = None
        st.sidebar.success("Đã xóa dữ liệu, bãi đỗ trở về trạng thái trống!")


# ==========================================
# 5. HEADER VÀ BANNER CHỈ SỐ KPI
# ==========================================
st.title("🅿️ Smart Parking Optimization System (AGV Model)")

total_cap = sum(b["capacity"] for b in st.session_state.blocks)
total_occ = sum(b["occupied"] for b in st.session_state.blocks)
total_avail = total_cap - total_occ
avail_blocks = sum(1 for b in st.session_state.blocks if not b["is_locked"] and b["occupied"] < b["capacity"])

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Tổng Sức chứa Bãi", f"{total_cap} xe")
kpi2.metric("Số xe Đang đỗ", f"{total_occ} xe")
kpi3.metric("Chỗ còn Trống", f"{total_avail} chỗ")
kpi4.metric("Số Block Khả dụng", f"{avail_blocks} / 9 Block")

st.markdown("---")


# ==========================================
# 6. MÔ PHỎNG SƠ ĐỒ BÃI ĐỖ XE 9 BLOCK
# ==========================================
col_map, col_info = st.columns([3.5, 1])

def get_block_dict():
    return {b["id"]: b for b in st.session_state.blocks}

def render_block_card_html(b, is_horizontal=False):
    last_res = st.session_state.last_assigned_res
    last_b_id = last_res["assigned_block"]["id"] if isinstance(last_res, dict) else None
    
    is_assigned = (last_b_id == b["id"])
    pct = int((b["occupied"] / b["capacity"]) * 100)

    if b["is_locked"]:
        status_tag = '<span style="background-color: #475569; color: #ffffff; padding: 2px 4px; border-radius: 4px; font-size: 9px; font-weight: bold; white-space: nowrap;">🔒 KHÓA</span>'
        bg_gradient = "linear-gradient(145deg, #e2e8f0, #cbd5e1)"
        border_style = "2px solid #64748b"
        shadow_style = "box-shadow: 0 3px 6px rgba(0,0,0,0.08);"
        text_color = "#1e293b"
    elif is_assigned:
        status_tag = '<span style="background-color: #15803d; color: #ffffff; padding: 2px 4px; border-radius: 4px; font-size: 9px; font-weight: bold; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">🎯 AGV CHỌN</span>'
        bg_gradient = "linear-gradient(145deg, #dcfce7, #bbf7d0)"
        border_style = "2.5px solid #16a34a"
        shadow_style = "box-shadow: 0 0 12px rgba(34, 197, 94, 0.35);"
        text_color = "#064e3b"
    elif b["occupied"] >= b["capacity"]:
        status_tag = '<span style="background-color: #b91c1c; color: #ffffff; padding: 2px 4px; border-radius: 4px; font-size: 9px; font-weight: bold; white-space: nowrap;">🔴 ĐÃ ĐẦY</span>'
        bg_gradient = "linear-gradient(145deg, #ffe4e6, #fecdd3)"
        border_style = "2px solid #ef4444"
        shadow_style = "box-shadow: 0 3px 6px rgba(0,0,0,0.08);"
        text_color = "#881337"
    else:
        status_tag = '<span style="background-color: #2563eb; color: #ffffff; padding: 2px 4px; border-radius: 4px; font-size: 9px; font-weight: bold; white-space: nowrap;">🟢 TRỐNG</span>'
        bg_gradient = "linear-gradient(145deg, #ffffff, #f8fafc)"
        border_style = "2px solid #cbd5e1"
        shadow_style = "box-shadow: 0 3px 6px rgba(0,0,0,0.04);"
        text_color = "#0f172a"

    card_height = "85px" if is_horizontal else "105px"

    return f'<div style="width: 100%; height: {card_height}; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; align-items: center; background: {bg_gradient}; border: {border_style}; border-radius: 8px; text-align: center; font-family: system-ui, -apple-system, sans-serif; {shadow_style}"><div style="font-size: 12px; font-weight: 800; color: {text_color}; margin-bottom: 2px;">🏢 {b["name"]}</div><div style="margin-bottom: 3px;">{status_tag}</div><div style="font-size: 10px; font-weight: 700; color: {text_color}; margin-bottom: 3px;">{b["occupied"]} / {b["capacity"]} xe</div><div style="background-color: rgba(0,0,0,0.08); border-radius: 4px; height: 5px; width: 80%; overflow: hidden; border: 1px solid rgba(0,0,0,0.05);"><div style="background: {"linear-gradient(90deg, #f43f5e, #be123c)" if pct==100 else "linear-gradient(90deg, #3b82f6, #1d4ed8)"}; width: {pct}%; height: 100%;"></div></div></div>'

def render_exact_grid():
    bd = get_block_dict()

    path_v = '<div style="background: #f1f5f9; border: 1px dashed #cbd5e1; border-radius: 4px; height: 105px; width: 8px; display: flex; align-items: center; justify-content: center; writing-mode: vertical-rl; font-size: 8px; color: #94a3b8;">↕</div>'

    grid_layout_html = f'''<div style="background-color: #ffffff; border-radius: 16px; padding: 14px; border: 2px solid #cbd5e1; box-shadow: 0 4px 12px rgba(0,0,0,0.03); width: 100%; box-sizing: border-box;">
<div style="display: grid; grid-template-columns: 1fr 12px 3.2fr 12px 1fr; gap: 8px; align-items: stretch; margin-bottom: 12px;">

<!-- CỘT CÁNH TRÁI: BLOCK 8 (TRÊN) & BLOCK 9 (DƯỚI) -->
<div style="display: flex; flex-direction: column; justify-content: space-between; gap: 12px;">
{render_block_card_html(bd["Block 8"])}
{render_block_card_html(bd["Block 9"])}
</div>

<!-- LẮP LÀN AGV DỌC TRÁI -->
<div style="background: repeating-linear-gradient(180deg, #f1f5f9, #f1f5f9 10px, #e2e8f0 10px, #e2e8f0 20px); border: 1px dashed #cbd5e1; border-radius: 6px; display: flex; align-items: center; justify-content: center; writing-mode: vertical-rl; font-size: 8px; font-weight: 700; color: #64748b; letter-spacing: 1px;">
↕ LÀN AGV DỌC TRÁI
</div>

<!-- KHU TRUNG TÂM -->
<div style="display: flex; flex-direction: column; gap: 8px; align-items: center;">
<!-- BLOCK 6 (KHỐI NGANG TRÊN) -->
<div style="width: 100%;">{render_block_card_html(bd["Block 6"], is_horizontal=True)}</div>

<!-- LÀN AGV NGANG 1 -->
<div style="background: repeating-linear-gradient(90deg, #f1f5f9, #f1f5f9 10px, #e2e8f0 10px, #e2e8f0 20px); border: 1px dashed #cbd5e1; border-radius: 6px; padding: 2px 4px; width: 100%; text-align: center; font-size: 8px; font-weight: 700; color: #64748b;">
↔ LÀN DI CHUYỂN AGV (HÀNG NGANG 1)
</div>

<!-- BLOCK 5 (KHỐI NGANG DƯỚI) -->
<div style="width: 100%;">{render_block_card_html(bd["Block 5"], is_horizontal=True)}</div>

<!-- LÀN AGV NGANG 2 -->
<div style="background: repeating-linear-gradient(90deg, #f1f5f9, #f1f5f9 10px, #e2e8f0 10px, #e2e8f0 20px); border: 1px dashed #cbd5e1; border-radius: 6px; padding: 2px 4px; width: 100%; text-align: center; font-size: 8px; font-weight: 700; color: #64748b;">
↔ LÀN DI CHUYỂN AGV (HÀNG NGANG 2)
</div>

<!-- HÀNG 3 BLOCK DỌC: BLOCK 1, BLOCK 2, BLOCK 3 -->
<div style="display: grid; grid-template-columns: 1fr auto 1fr auto 1fr; gap: 4px; align-items: center; width: 100%;">
<div>{render_block_card_html(bd["Block 1"])}</div>
{path_v}
<div>{render_block_card_html(bd["Block 2"])}</div>
{path_v}
<div>{render_block_card_html(bd["Block 3"])}</div>
</div>
</div>

<!-- LẮP LÀN AGV DỌC PHẢI -->
<div style="background: repeating-linear-gradient(180deg, #f1f5f9, #f1f5f9 10px, #e2e8f0 10px, #e2e8f0 20px); border: 1px dashed #cbd5e1; border-radius: 6px; display: flex; align-items: center; justify-content: center; writing-mode: vertical-rl; font-size: 8px; font-weight: 700; color: #64748b; letter-spacing: 1px;">
↕ LÀN AGV DỌC PHẢI
</div>

<!-- CỘT CÁNH PHẢI: BLOCK 7 (TRÊN) & BLOCK 4 (DƯỚI) -->
<div style="display: flex; flex-direction: column; justify-content: space-between; gap: 12px;">
{render_block_card_html(bd["Block 7"])}
{render_block_card_html(bd["Block 4"])}
</div>
</div>

<!-- VÙNG ĐỆM XOAY SỞ AGV & CỔNG ENTRY / EXIT -->
<div style="background: linear-gradient(135deg, #f8fafc, #f1f5f9); border: 2px dashed #94a3b8; border-radius: 10px; padding: 8px 12px; display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: 6px;">
<div style="background-color: #fee2e2; color: #991b1b; border: 1.5px solid #f87171; padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: 800;">
🚪 EXIT (CỔNG RA)
</div>
<div style="text-align: center; flex-grow: 1;">
<div style="font-size: 10px; font-weight: 800; color: #334155;">
📸 VÙNG ĐỆM THAO TÁC XOAY SỞ AGV & TRẠM QUÉT CAMERA AI
</div>
<div style="font-size: 8px; color: #64748b; font-weight: 600;">
🤖 Thu thập dữ liệu trọng lượng, quét biển số & điều hướng Robot quay 360°
</div>
</div>
<div style="background-color: #dcfce7; color: #166534; border: 1.5px solid #4ade80; padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: 800;">
🚪 ENTRY (CỔNG VÀO)
</div>
</div>
</div>'''

    st.markdown(grid_layout_html, unsafe_allow_html=True)

# --- CỘT TRÁI: SƠ ĐỒ MẶT BẰNG 9 BLOCK ---
with col_map:
    st.subheader("🗺️ Sơ đồ Mặt bằng Bãi đỗ xe (9 Block)")
    render_exact_grid()

# --- CỘT PHẢI: CHỈ DẪN ROBOT AGV & THÔNG TIN ---
with col_info:
    st.subheader("📌 Chỉ dẫn Robot AGV")
    
    last_res = st.session_state.last_assigned_res
    
    if last_res == "FULL":
        st.error("⛔ **THÔNG BÁO AGV:**\n\nTẤT CẢ CÁC BLOCK ĐỀU ĐÃ KÍN CHỖ HOẶC BỊ KHÓA.")
    elif isinstance(last_res, dict):
        assigned_b = last_res["assigned_block"]
        st.success(f"""
        🎯 **GÁN VẬN CHUYỂN ĐẾN:**
        ### **{assigned_b['name']}**
        * **Sức chứa:** `{assigned_b['occupied']} / {assigned_b['capacity']} xe`
        * **Tiêu thụ pin AGV dự kiến:** `{last_res['agv_energy']} kWh`
        """)
    else:
        st.info("🎯 **Chưa có lệnh vận chuyển.**\n\nNhấn 'ROBOT AGV VẬN HÀNH ĐỖ XE' ở thanh bên để gán khối đỗ.")

    st.markdown("---")
    st.subheader("ℹ️ Thông tin Khai báo Xe")
    
    st.markdown(f"""
    * **Khối lượng xe:** `{weight} kg`
    * **Thời gian đỗ:** `{duration} giờ`
    * **Đối tượng:** {"⚡ Ưu tiên" if is_priority else "🚗 Thông thường"}
    * **Điểm Tối ưu (Urgency):** `{round((weight/1000.0)*2.5 + (24.0/(duration+0.5))*3.5, 1)} điểm`
    """)

    st.markdown("---")
    st.caption("**Quy tắc sơ đồ 9 Block:**")
    st.caption("🟢 **TRỐNG**: Khối đỗ còn chỗ")
    st.caption("🔴 **ĐÃ ĐẦY**: Khối đỗ đã kín xe")
    st.caption("🔒 **KHÓA**: Khối đỗ tạm khóa")
    st.caption("🎯 **AGV CHỌN**: Vừa được Robot chọn")
