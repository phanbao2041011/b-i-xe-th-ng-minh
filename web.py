import streamlit as st

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
BLOCK_DISTANCES = {
    "Block 1": 4, "Block 2": 3, "Block 3": 2, "Block 4": 1,
    "Block 5": 5, "Block 6": 7, "Block 7": 2, "Block 8": 8, "Block 9": 6
}

def calculate_urgency(weight, duration):
    """Tính điểm cấp thiết dựa trên Khối lượng và Thời gian đỗ"""
    score = (weight / 1000.0) * 2.5 + (24.0 / (duration + 0.5)) * 3.5
    return round(score, 2)

def calculate_agv_energy(block_id, weight):
    """Tính toán mức tiêu thụ năng lượng của Robot AGV (kWh)"""
    dist = BLOCK_DISTANCES.get(block_id, 5)
    e_base = 0.03
    k_load = 0.000025
    energy = dist * (e_base + k_load * weight)
    return round(energy, 2)

def find_optimal_block(weight, duration):
    """Thuật toán sàng lọc và lựa chọn Block tối ưu"""
    urgency = calculate_urgency(weight, duration)
    valid_blocks = [b for b in st.session_state.blocks if not b["is_locked"] and b["occupied"] < b["capacity"]]
    
    if not valid_blocks:
        return "FULL"

    best_block = None
    min_cost = float('inf')
    w1, w2 = 0.6, 0.4

    for b in valid_blocks:
        b_id = b["id"]
        energy = calculate_agv_energy(b_id, weight)
        
        ideal_score = 15.0
        if b_id in ["Block 4", "Block 7"]:
            ideal_score = 25.0
        elif b_id in ["Block 1", "Block 9"]:
            ideal_score = 20.0
        elif b_id in ["Block 5", "Block 6"]:
            ideal_score = 8.0

        occupancy_ratio = b["occupied"] / b["capacity"]
        penalty = occupancy_ratio * 3.0
        
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
duration = st.sidebar.number_input("⏱️ Thời gian đỗ dự kiến (giờ):", min_value=0.5, max_value=72.0, value=2.0, step=0.5)
weight = st.sidebar.number_input("⚖️ Khối lượng xe (kg):", min_value=500, max_value=3500, value=1500, step=50)

st.sidebar.markdown("---")

if st.sidebar.button("🚗 ROBOT AGV VẬN HÀNH ĐỖ XE", type="primary", use_container_width=True):
    res = find_optimal_block(weight, duration)
    st.session_state.last_assigned_res = res
    if res != "FULL" and isinstance(res, dict):
        target_id = res["assigned_block"]["id"]
        for b in st.session_state.blocks:
            if b["id"] == target_id:
                b["occupied"] += 1
                break
        st.sidebar.success(f"✅ Robot AGV đã vận chuyển xe vào **{target_id}**!")
    else:
        st.sidebar.error("❌ Tất cả các Block đều đã KÍN CHỖ hoặc BỊ KHÓA!")

st.sidebar.markdown("---")

st.sidebar.subheader("⚙️ Chế độ Quản trị viên (Admin)")
admin_mode = st.sidebar.checkbox("🔓 Bật Chế độ Quản trị", value=True)

if admin_mode:
    st.sidebar.caption("🔒 **Quản lý Khóa / Mở Block:**")
    selected_to_lock = st.sidebar.multiselect(
        "Chọn Block muốn Khóa:",
        options=[b["id"] for b in st.session_state.blocks],
        default=[b["id"] for b in st.session_state.blocks if b["is_locked"]]
    )
    
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
# 6. MÔ PHỎNG SƠ ĐỒ 9 BLOCK (TĂNG 25% CHIỀU DÀI BLOCK DỌC)
# ==========================================
col_map, col_info = st.columns([3.5, 1])

def get_block_dict():
    return {b["id"]: b for b in st.session_state.blocks}

def render_block_card_html
