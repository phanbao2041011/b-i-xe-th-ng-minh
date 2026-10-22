import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from PIL import Image
import time
import io

# ---------------------------------------------------------
# 1. CẤU HÌNH TRANG STREAMLIT
# ---------------------------------------------------------
st.set_page_config(
    page_title="Mô Phỏng AGV Dẫn Xe Vào Block Đỗ",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Mô Phỏng AGV Dẫn Xe Vào Block Đỗ Xe")
st.markdown("Hệ thống hiển thị **chính xác sơ đồ mặt bằng thực tế**, tự động chọn Block và **cho Robot AGV chạy trực tiếp** từ Cổng vào vị trí đỗ.")

# ---------------------------------------------------------
# 2. KHỞI TẠO TỌA ĐỘ 9 BLOCK & TUYẾN ĐƯỜNG AGV THEO BẢN VẼ
# ---------------------------------------------------------
@st.cache_data
def get_map_nodes():
    """
    Tọa độ chuẩn hóa (x: 0->100, y: 0->100) khớp với vị trí ảnh sơ đồ bản vẽ.
    - Cổng ENTRANCE nằm ở tọa độ: (49.5, 3.5)
    """
    blocks = [
        {"id": "Block 1", "cx": 25.5, "cy": 25.0, "cap": 24, "occ": 18, "desc": "Khu trung tâm 1"},
        {"id": "Block 2", "cx": 41.5, "cy": 25.0, "cap": 24, "occ": 12, "desc": "Khu trung tâm 2"},
        {"id": "Block 3", "cx": 62.0, "cy": 25.0, "cap": 24, "occ": 21, "desc": "Khu trung tâm 3"},
        {"id": "Block 4", "cx": 78.0, "cy": 25.0, "cap": 24, "occ": 10, "desc": "Khu trung tâm 4"},
        {"id": "Block 5", "cx": 50.0, "cy": 84.0, "cap": 60, "occ": 54, "desc": "Dãy ngang trên"},
        {"id": "Block 6", "cx": 50.0, "cy": 64.0, "cap": 60, "occ": 38, "desc": "Dãy ngang giữa"},
        {"id": "Block 7", "cx": 67.0, "cy": 45.0, "cap": 30, "occ": 30, "desc": "Dãy ngang nhỏ (FULL)"},
        {"id": "Block 8", "cx": 7.0,  "cy": 50.0, "cap": 48, "occ": 25, "desc": "Dãy dọc Trái"},
        {"id": "Block 9", "cx": 95.0, "cy": 50.0, "cap": 48, "occ": 42, "desc": "Dãy dọc Phải"},
    ]
    df = pd.DataFrame(blocks)
    entrance_x, entrance_y = 49.5, 3.5
    df["distance"] = np.abs(df["cx"] - entrance_x) + np.abs(df["cy"] - entrance_y)
    return df

df_blocks = get_map_nodes().copy()

# Định nghĩa các điểm rẽ trên đường ống AGV (Waypoints) từ Entrance (49.5, 3.5)
def get_agv_route(target_block_id):
    entrance = (49.5, 3.5)
    
    # Tuyến đường di chuyển từng bước khớp với các mũi tên xanh dương trên bản vẽ
    routes = {
        "Block 1": [entrance, (49.5, 11.5), (25.5, 11.5), (25.5, 25.0)],
        "Block 2": [entrance, (49.5, 11.5), (41.5, 11.5), (41.5, 25.0)],
        "Block 3": [entrance, (49.5, 11.5), (62.0, 11.5), (62.0, 25.0)],
        "Block 4": [entrance, (49.5, 11.5), (78.0, 11.5), (78.0, 25.0)],
        "Block 7": [entrance, (49.5, 11.5), (67.0, 11.5), (67.0, 45.0)],
        "Block 6": [entrance, (49.5, 11.5), (21.5, 11.5), (21.5, 64.0), (50.0, 64.0)],
        "Block 5": [entrance, (49.5, 11.5), (82.5, 11.5), (82.5, 84.0), (50.0, 84.0)],
        "Block 8": [entrance, (49.5, 11.5), (21.5, 11.5), (14.0, 11.5), (14.0, 50.0), (7.0, 50.0)],
        "Block 9": [entrance, (49.5, 11.5), (82.5, 11.5), (88.0, 11.5), (88.0, 50.0), (95.0, 50.0)],
    }
    return routes.get(target_block_id, [entrance])

# ---------------------------------------------------------
# 3. SIDEBAR INPUTS
# ---------------------------------------------------------
st.sidebar.header("🖼️ 1. Cấu Hình Ảnh Sơ Đồ")
uploaded_file = st.sidebar.file_uploader("Tải lên ảnh sơ đồ mặt bằng (JPG/PNG):", type=["jpg", "jpeg", "png"])

bg_img = None
if uploaded_file is not None:
    bg_img = Image.open(uploaded_file)
else:
    try:
        bg_img = Image.open("map.jpg") # Đọc file map.jpg trong cùng thư mục GitHub
    except FileNotFoundError:
        bg_img = None

st.sidebar.markdown("---")
st.sidebar.header("📥 2. Thông Tin Xe Nhập Bãi")

preset = st.sidebar.selectbox(
    "Chọn kịch bản nhanh:",
    ["Tùy chỉnh", "Xe điện nặng đỗ ngắn hạn (1h)", "Xe SUV trung bình đỗ trong ngày (6h)", "Xe Sedan nhẹ đỗ dài hạn (48h)"]
)

if preset == "Xe điện nặng đỗ ngắn hạn (1h)":
    init_w, init_t = 2700, 1.0
elif preset == "Xe SUV trung bình đỗ trong ngày (6h)":
    init_w, init_t = 2000, 6.0
elif preset == "Xe Sedan nhẹ đỗ dài hạn (48h)":
    init_w, init_t = 1300, 48.0
else:
    init_w, init_t = 1800, 3.0

car_weight = st.sidebar.number_input("⚖️ Khối lượng xe (kg):", min_value=800, max_value=4000, value=init_w, step=100)
park_duration = st.sidebar.number_input("⏱️ Thời gian đỗ (giờ):", min_value=0.5, max_value=168.0, value=init_t, step=0.5)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 3. Trọng Số Tối Ưu")
w_e = st.sidebar.slider("Ưu tiên Năng lượng AGV:", 0.0, 1.0, 0.45, 0.05)
w_r = st.sidebar.slider("Ưu tiên Tốc độ lấy xe:", 0.0, 1.0, 0.35, 0.05)
w_b = st.sidebar.slider("Ưu tiên Cân bằng tải:", 0.0, 1.0, 0.20, 0.05)  # <--- Bổ sung ngoặc ) ở đây nếu thiếu

# -----------------------------------------------------
# 4. HÀM TÍNH TOÁN CHỌN BLOCK
# ---------------------------------------------------------
def evaluate_blocks(df, weight, duration, we, wr, wb):
    calc = df.copy()
    calc["available"] = calc["cap"] - calc["occ"]
    calc["is_full"] = calc["available"] <= 0
    
    alpha, beta, gamma = 0.01, 2.5, 3.0
    calc["raw_energy"] = weight * (alpha * calc["distance"] + beta)
    calc["raw_retrieval"] = (calc["distance"] + gamma) / (duration + 0.1)
    calc["occ_rate"] = calc["occ"] / calc["cap"]
    calc["raw_balance"] = calc["occ_rate"] ** 2

    def min_max(s):
        return (s - s.min()) / (s.max() - s.min()) if s.max() != s.min() else pd.Series(0.0, index=s.index)

    tot_w = we + wr + wb
    we_n, wr_n, wb_n = (we/tot_w, wr/tot_w, wb/tot_w) if tot_w > 0 else (1/3, 1/3, 1/3)

    calc["norm_e"] = min_max(calc["raw_energy"])
    calc["norm_r"] = min_max(calc["raw_retrieval"])
    calc["norm_b"] = min_max(calc["raw_balance"])

    calc["score"] = (we_n * calc["norm_e"] + wr_n * calc["norm_r"] + wb_n * calc["norm_b"])
    calc.loc[calc["is_full"], "score"] = 999.0
    return calc
