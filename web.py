import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. CẤU HÌNH TRANG STREAMLIT (GIAO DIỆN SÁNG, SẠCH ĐẸP)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Hệ thống Tối ưu Bãi đỗ xe AGV",
    page_icon="🚗",
    layout="wide"
)

# Custom CSS tạo phong cách thẻ bo tròn thẩm mỹ như giao diện mẫu
st.markdown("""
<style>
    .main { background-color: #F8FAFC; }
    .stButton>button {
        background-color: #EF4444;
        color: white;
        font-weight: bold;
        font-size: 16px;
        border-radius: 10px;
        height: 48px;
        width: 100%;
        border: none;
    }
    .stButton>button:hover { background-color: #DC2626; color: white; }
    .guide-card {
        background-color: #ECFDF5;
        border: 2px solid #10B981;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        color: #065F46;
        font-weight: bold;
        font-size: 20px;
        margin-bottom: 20px;
    }
    .info-card {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. KHỞI TẠO TỌA ĐỘ 9 BLOCK BÃI ĐỖ XE
# ---------------------------------------------------------
@st.cache_data
def get_blocks_data():
    blocks = [
        # Dãy dọc Trái (8) & Phải (9)
        {"id": "BLOCK 8", "x0": 4,  "x1": 12, "y0": 15, "y1": 85, "cx": 8,  "cy": 50, "cap": 48, "occ": 25, "desc": "Dãy dọc Trái"},
        {"id": "BLOCK 9", "x0": 88, "x1": 96, "y0": 15, "y1": 85, "cx": 92, "cy": 50, "cap": 48, "occ": 42, "desc": "Dãy dọc Phải"},

        # 4 Block Trung tâm dưới (1, 2, 3, 4)
        {"id": "BLOCK 1", "x0": 18, "x1": 30, "y0": 15, "y1": 38, "cx": 24, "cy": 26.5, "cap": 24, "occ": 18, "desc": "Khu Trung tâm 1"},
        {"id": "BLOCK 2", "x0": 34, "x1": 46, "y0": 15, "y1": 38, "cx": 40, "cy": 26.5, "cap": 24, "occ": 12, "desc": "Khu Trung tâm 2"},
        {"id": "BLOCK 3", "x0": 54, "x1": 66, "y0": 15, "y1": 38, "cx": 60, "cy": 26.5, "cap": 24, "occ": 21, "desc": "Khu Trung tâm 3"},
        {"id": "BLOCK 4", "x0": 70, "x1": 82, "y0": 15, "y1": 38, "cx": 76, "cy": 26.5, "cap": 24, "occ": 10, "desc": "Khu Trung tâm 4"},

        # Block Dãy Ngang (7, 6, 5)
        {"id": "BLOCK 7", "x0": 54, "x1": 82, "y0": 43, "y1": 51, "cx": 68, "cy": 47, "cap": 30, "occ": 30, "desc": "Dãy ngang nhỏ (FULL)"},
        {"id": "BLOCK 6", "x0": 18, "x1": 82, "y0": 57, "y1": 69, "cx": 50, "cy": 63, "cap": 60, "occ": 38, "desc": "Dãy ngang giữa"},
        {"id": "BLOCK 5", "x0": 18, "x1": 82, "y0": 75, "y1": 87, "cx": 50, "cy": 81, "cap": 60, "occ": 54, "desc": "Dãy ngang trên"},
    ]
    df = pd.DataFrame(blocks)
    df["distance"] = np.abs(df["cx"] - 50) + np.abs(df["cy"] - 0)
    return df

df_blocks = get_blocks_data().copy()

# ---------------------------------------------------------
# 3. SIDEBAR - BẢNG KHAI BÁO XE VÀO CỔNG
# ---------------------------------------------------------
st.sidebar.header("📋 Khai báo Xe vào Cổng")

car_weight = st.sidebar.number_input("⚖️ Khối lượng xe (kg):", min_value=800, max_value=4000, value=1800, step=100)
park_duration = st.sidebar.number_input("⏱️ Thời gian đỗ dự kiến (giờ):", min_value=0.5, max_value=168.0, value=3.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Trọng số Tối ưu")
w_energy = st.sidebar.slider("Tiết kiệm pin AGV:", 0.0, 1.0, 0.45, 0.05)
w_retrieval = st.sidebar.slider("Tốc độ trả xe:", 0.0, 1.0, 0.35, 0.05)
w_balance = st.sidebar.slider("Cân bằng tải bãi:", 0.0, 1.0, 0.20, 0.05)

btn_submit = st.sidebar.button("🚗 ĐỖ XE THEO GỢI Ý")

# ---------------------------------------------------------
# 4. THUẬT TOÁN TÍNH CHỌN BLOCK TỐI ƯU
# ---------------------------------------------------------
def select_best_block(df, weight, duration, we, wr, wb):
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

    tot = we + wr + wb
    we_n, wr_n, wb_n = (we/tot, wr/tot, wb/tot) if tot > 0 else (1/3, 1/3, 1/3)

    calc["norm_e"] = min_max(calc["raw_energy"])
    calc["norm_r"] = min_max(calc["raw_retrieval"])
    calc["norm_b"] = min_max(calc["raw_balance"])

    calc["score"] = we_n * calc["norm_e"] + wr_n * calc["norm_r"] + wb_n * calc["norm_b"]
    calc.loc[calc["is_full"], "score"] = 999.0
    return calc

res_df = select_best_block(df_blocks, car_weight, park_duration, w_energy, w_retrieval, w_balance)
valid_blocks = res_df[~res_df["is_full"]]
best_block = valid_blocks.loc[valid_blocks["score"].idxmin()] if not valid_blocks.empty else None

# ---------------------------------------------------------
# 5. CHIA BỐ CỤC CHÍNH (SƠ ĐỒ TRỰC QUAN + CHỈ DẪN HỆ THỐNG)
# ---------------------------------------------------------
col_main, col_info = st.columns([7, 3])

with col_main:
    st.subheader("🗺️ Sơ đồ Mặt bằng Bãi đỗ xe")

    fig = go.Figure()

    # 1. Tường bao bãi đỗ
    fig.add_shape(type="rect", x0=0, y0=0, x1=100, y1=95, line=dict(color="#CBD5E1", width=3), fillcolor="#F8FAFC")

    # 2. Đường đi AGV chính (Màu xám nhạt)
    agv_lanes = [
        {"x": [14, 14], "y": [6, 90]}, {"x": [86, 86], "y": [6, 90]}, {"x": [50, 50], "y": [0, 53]},
        {"x": [14, 86], "y": [6, 6]}, {"x": [14, 86], "y": [53, 53]}, {"x": [14, 86], "y": [72, 72]}, {"x": [14, 86], "y": [90, 90]}
    ]
    for lane in agv_lanes:
        fig.add_trace(go.Scatter(x=lane["x"], y=lane["y"], mode="lines", line=dict(color="#E2E8F0", width=8), showlegend=False, hoverinfo="none"))

    # 3. Cổng ENTRANCE
    fig.add_shape(type="rect", x0=42, y0=-4, x1=58, y1=1, fillcolor="#F59E0B", line=dict(color="#B45309", width=2))
    fig.add_trace(go.Scatter(x=[50], y=[-1.5], mode="text", text=["<b>🚪 CỔNG VÀO</b>"], textfont=dict(color="white", size=11), showlegend=False))

    # 4. Vẽ 9 Block
    for _, row in res_df.iterrows():
        is_selected = (best_block is not None) and (row["id"] == best_block["id"])

        if row["is_full"]:
            fill_col = "#FCA5A5"      # Đỏ nhạt (Đã đầy)
            border_col = "#EF4444"
            txt_status = "ĐÃ ĐẦY"
            txt_color = "#7F1D1D"
        elif is_selected:
            fill_col = "#10B981"      # Xanh lá sáng (Được chọn)
            border_col = "#047857"
            txt_status = "⭐ CHỌN"
            txt_color = "#FFFFFF"
        else:
            fill_bg = "#FEF08A"       # Vàng nhạt (Còn trống)
            border_col = "#EAB308"
            txt_status = "TRỐNG"
            txt_color = "#713F12"

        fig.add_shape(
            type="rect",
            x0=row["x0"], y0=row["y0"],
            x1=row["x1"], y1=row["y1"],
            fillcolor=fill_col if not ('fill_bg' in locals() and not is_selected and not row["is_full"]) else fill_bg,
            line=dict(color=border_col, width=2),
            opacity=0.9
        )

        fig.add_trace(go.Scatter(
            x=[row["cx"]], y=[row["cy"]],
            mode="text",
            text=[f"<b>{row['id']}</b><br><size=9>{txt_status}</size>"],
            textfont=dict(color=txt_color, size=11),
            hoverinfo="text",
            hovertext=f"<b>{row['id']}</b> ({row['desc']})<br>Trống: {row['available']}/{row['cap']} ô",
            showlegend=False
        ))

    # 5. MŨI TÊN CHỈ DẪN AGV ĐẾN BLOCK ĐƯỢC CHỌN (Đường Xanh Lá)
    if best_block is not None:
        target_x, target_y = best_block["cx"], best_block["cy"]
        
        # Tuyến đường gấp khúc từ Cổng (50, 0)
