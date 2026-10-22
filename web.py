import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ---------------------------------------------------------
# 1. CẤU HÌNH TRANG STREAMLIT
# ---------------------------------------------------------
st.set_page_config(
    page_title="Mô Phỏng Sơ Đồ Mặt Bằng Block Bãi Đỗ AGV",
    page_icon="🚘",
    layout="wide"
)

st.title("🚘 Mô Phỏng Sơ Đồ Chọn Block Đỗ Xe AGV")
st.markdown("Hệ thống tự động tính toán **Block đỗ xe tối ưu** dựa trên **Trọng lượng xe** và **Thời gian đỗ** trực tiếp trên sơ đồ mặt bằng.")

# ---------------------------------------------------------
# 2. KHỞI TẠO TỌA ĐỘ BLOCK THEO BẢN VẼ KỸ THUẬT (2D LAYOUT)
# ---------------------------------------------------------
@st.cache_data
def get_map_data():
    """
    Toàn bộ tọa độ khung chữ nhật (x0, y0, x1, y1) mô phỏng chính xác bản vẽ CAD 9 Block.
    Cổng Entrance nằm ở đáy trung tâm: (50, 0).
    """
    blocks = [
        # Dãy dọc Trái & Phải
        {"id": "Block 8", "x0": 3,  "x1": 11, "y0": 12, "y1": 88, "cx": 7,  "cy": 50, "cap": 48, "occ": 25, "desc": "Dãy dọc Trái"},
        {"id": "Block 9", "x0": 89, "x1": 97, "y0": 12, "y1": 88, "cx": 93, "cy": 50, "cap": 48, "occ": 42, "desc": "Dãy dọc Phải"},
        
        # Cụm 4 Block Trung tâm dưới
        {"id": "Block 1", "x0": 17, "x1": 29, "y0": 12, "y1": 38, "cx": 23, "cy": 25, "cap": 24, "occ": 18, "desc": "Khu Trung tâm 1"},
        {"id": "Block 2", "x0": 33, "x1": 45, "y0": 12, "y1": 38, "cx": 39, "cy": 25, "cap": 24, "occ": 12, "desc": "Khu Trung tâm 2"},
        {"id": "Block 3", "x0": 55, "x1": 67, "y0": 12, "y1": 38, "cx": 61, "cy": 25, "cap": 24, "occ": 21, "desc": "Khu Trung tâm 3"},
        {"id": "Block 4", "x0": 71, "x1": 83, "y0": 12, "y1": 38, "cx": 77, "cy": 25, "cap": 24, "occ": 10, "desc": "Khu Trung tâm 4"},
        
        # Block Dãy Ngang
        {"id": "Block 7", "x0": 55, "x1": 83, "y0": 42, "y1": 50, "cx": 69, "cy": 46, "cap": 30, "occ": 30, "desc": "Dãy ngang nhỏ (Đầy)"}, # Giả lập đầy
        {"id": "Block 6", "x0": 17, "x1": 83, "y0": 56, "y1": 68, "cx": 50, "cy": 62, "cap": 60, "occ": 38, "desc": "Dãy ngang giữa"},
        {"id": "Block 5", "x0": 17, "x1": 83, "y0": 74, "y1": 86, "cx": 50, "cy": 80, "cap": 60, "occ": 54, "desc": "Dãy ngang trên"},
    ]
    df = pd.DataFrame(blocks)
    
    # Khoảng cách di chuyển đường băng AGV từ Entrance (50, 0) đến tâm Block (cx, cy)
    entrance_x, entrance_y = 50, 0
    df["distance"] = (np.abs(df["cx"] - entrance_x) + np.abs(df["cy"] - entrance_y)).astype(float)
    return df

df_blocks = get_map_data().copy()

# ---------------------------------------------------------
# 3. SIDEBAR - NHẬP DỮ LIỆU ĐỔ VÀO (KHỐI LƯỢNG & THỜI GIAN)
# ---------------------------------------------------------
st.sidebar.header("📥 Dữ Liệu Xe Nhập Bãi")

# Chọn nhanh kịch bản
preset = st.sidebar.selectbox(
    "Chọn nhanh mẫu xe:",
    ["Tùy chỉnh", "Xe điện đỗ ngắn hạn (Lấy gấp)", "Xe SUV trung bình (Đỗ trong ngày)", "Xe Sedan nhẹ (Đỗ dài hạn)"]
)

if preset == "Xe điện đỗ ngắn hạn (Lấy gấp)":
    default_w, default_t = 2600, 1.0
elif preset == "Xe SUV trung bình (Đỗ trong ngày)":
    default_w, default_t = 1900, 6.0
elif preset == "Xe Sedan nhẹ (Đỗ dài hạn)":
    default_w, default_t = 1200, 48.0
else:
    default_w, default_t = 1800, 3.0

car_weight = st.sidebar.number_input("⚖️ Khối lượng xe W_car (kg):", min_value=800, max_value=4000, value=default_w, step=100)
park_duration = st.sidebar.number_input("⏱️ Thời gian đỗ T_park (giờ):", min_value=0.5, max_value=168.0, value=default_t, step=0.5)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Trọng Số Thuật Toán")
w_energy = st.sidebar.slider("Tiết kiệm pin AGV (Năng lượng):", 0.0, 1.0, 0.45, 0.05)
w_retrieval = st.sidebar.slider("Tốc độ lấy xe (Thời gian):", 0.0, 1.0, 0.35, 0.05)
w_balance = st.sidebar.slider("Cân bằng tải bãi đỗ:", 0.0, 1.0, 0.20, 0.05)

# Chuẩn hóa trọng số
tot_w = w_energy + w_retrieval + w_balance
w_e, w_r, w_b = (w_energy/tot_w, w_retrieval/tot_w, w_balance/tot_w) if tot_w > 0 else (1/3, 1/3, 1/3)

# ---------------------------------------------------------
# 4. HÀM TÍNH TOÁN THUẬT TOÁN CHỌN BLOCK
# ---------------------------------------------------------
def calculate_optimal_block(df, weight, duration, we, wr, wb):
    calc = df.copy()
    calc["available"] = calc["cap"] - calc["occ"]
    calc["is_full"] = calc["available"] <= 0
    
    alpha, beta, gamma = 0.01, 2.5, 3.0
    
    # 1. Chi phí năng lượng AGV
    calc["raw_energy"] = weight * (alpha * calc["distance"] + beta)
    
    # 2. Chi phí truy xuất (Thời gian đỗ ngắn -> Phạt block ở xa)
    calc["raw_retrieval"] = (calc["distance"] + gamma) / (duration + 0.1)
    
    # 3. Chi phí cân bằng tải bãi
    calc["occ_rate"] = calc["occ"] / calc["cap"]
    calc["raw_balance"] = calc["occ_rate"] ** 2

    # Chuẩn hóa Min-Max [0, 1]
    def min_max(s):
        return (s - s.min()) / (s.max() - s.min()) if s.max() != s.min() else pd.Series(0.0, index=s.index)

    calc["norm_energy"] = min_max(calc["raw_energy"])
    calc["norm_retrieval"] = min_max(calc["raw_retrieval"])
    calc["norm_balance"] = min_max(calc["raw_balance"])

    # Tổng điểm chi phí (Càng nhỏ càng tốt)
    calc["score"] = (we * calc["norm_energy"] + wr * calc["norm_retrieval"] + wb * calc["norm_balance"])
