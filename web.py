import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ---------------------------------------------------------
# 1. CẤU HÌNH TRANG STREAMLIT
# ---------------------------------------------------------
st.set_page_config(
    page_title="Hệ Thống Tối Ưu Chọn Block Bãi Đỗ AGV",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Mô Phỏng Thuật Toán Chọn Block Đỗ Xe AGV")
st.markdown("Hệ thống tự động tính toán **Block đỗ xe tối ưu** dựa trên **Khối lượng xe** và **Thời gian đỗ** trực tiếp trên sơ đồ mặt bằng 9 Block.")

# ---------------------------------------------------------
# 2. KHỞI TẠO TỌA ĐỘ BLOCK THEO BẢN VẼ KỸ THUẬT 2D
# ---------------------------------------------------------
@st.cache_data
def get_parking_layout():
    """
    Tọa độ chuẩn hóa các Block dựa trên bản vẽ mặt bằng:
    - Cổng ENTRANCE nằm ở đáy trung tâm: (50, 0)
    - Block 1, 2, 3, 4: Cụm trung tâm phía dưới
    - Block 5, 6, 7: Các dãy nằm ngang phía trên
    - Block 8, 9: Hai dãy dọc hai bên cánh (Trái / Phải)
    """
    blocks = [
        # Dãy dọc Trái & Phải
        {"id": "Block 8", "x0": 2,  "x1": 10, "y0": 15, "y1": 85, "cx": 6,  "cy": 50, "cap": 48, "occ": 25, "desc": "Dãy dọc Trái"},
        {"id": "Block 9", "x0": 90, "x1": 98, "y0": 15, "y1": 85, "cx": 94, "cy": 50, "cap": 48, "occ": 42, "desc": "Dãy dọc Phải"},
        
        # Cụm 4 Block Trung tâm dưới
        {"id": "Block 1", "x0": 16, "x1": 28, "y0": 15, "y1": 38, "cx": 22, "cy": 26.5, "cap": 24, "occ": 18, "desc": "Khu Trung tâm 1"},
        {"id": "Block 2", "x0": 32, "x1": 44, "y0": 15, "y1": 38, "cx": 38, "cy": 26.5, "cap": 24, "occ": 12, "desc": "Khu Trung tâm 2"},
        {"id": "Block 3", "x0": 56, "x1": 68, "y0": 15, "y1": 38, "cx": 62, "cy": 26.5, "cap": 24, "occ": 21, "desc": "Khu Trung tâm 3"},
        {"id": "Block 4", "x0": 72, "x1": 84, "y0": 15, "y1": 38, "cx": 78, "cy": 26.5, "cap": 24, "occ": 10, "desc": "Khu Trung tâm 4"},
        
        # Block Dãy Ngang
        {"id": "Block 7", "x0": 56, "x1": 84, "y0": 43, "y1": 50, "cx": 70, "cy": 46.5, "cap": 30, "occ": 30, "desc": "Dãy ngang nhỏ (FULL)"},
        {"id": "Block 6", "x0": 16, "x1": 84, "y0": 56, "y1": 68, "cx": 50, "cy": 62, "cap": 60, "occ": 38, "desc": "Dãy ngang giữa"},
        {"id": "Block 5", "x0": 16, "x1": 84, "y0": 74, "y1": 86, "cx": 50, "cy": 80, "cap": 60, "occ": 54, "desc": "Dãy ngang trên"},
    ]
    df = pd.DataFrame(blocks)
    
    # Khoảng cách quãng đường di chuyển AGV từ Entrance (50, 0)
    entrance_x, entrance_y = 50, 0
    df["distance"] = (np.abs(df["cx"] - entrance_x) + np.abs(df["cy"] - entrance_y)).astype(float)
    return df

df_blocks = get_parking_layout().copy()

# ---------------------------------------------------------
# 3. SIDEBAR - ĐẦU VÀO DỮ LIỆU & TRỌNG SỐ THUẬT TOÁN
# ---------------------------------------------------------
st.sidebar.header("📥 1. Thông Tin Xe Nhập Bãi")

preset = st.sidebar.selectbox(
    "Chọn nhanh kịch bản xe:",
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

car_weight = st.sidebar.number_input("⚖️ Khối lượng xe W_car (kg):", min_value=800, max_value=4000, value=init_w, step=100)
park_duration = st.sidebar.number_input("⏱️ Thời gian đỗ T_park (giờ):", min_value=0.5, max_value=168.0, value=init_t, step=0.5)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 2. Trọng Số Thuật Toán")
w_energy = st.sidebar.slider("Tiết kiệm pin AGV (Năng lượng):", 0.0, 1.0, 0.45, 0.05)
w_retrieval = st.sidebar.slider("Tốc độ trả xe (Thời gian):", 0.0, 1.0, 0.35, 0.05)
w_balance = st.sidebar.slider("Cân bằng tải bãi đỗ:", 0.0, 1.0, 0.20, 0.05)

# ---------------------------------------------------------
# 4. HÀM TÍNH TOÁN CORE ALGORITHM
# ---------------------------------------------------------
def run_selection_algorithm(df, weight, duration, we, wr, wb):
    calc = df.copy()
    calc["available"] = calc["cap"] - calc["occ"]
    calc["is_full"] = calc["available"] <= 0
    
    alpha, beta, gamma = 0.01, 2.5, 3.0
    
    # 1. Chi phí năng lượng
    calc["raw_energy"] = weight * (alpha * calc["distance"] + beta)
    
    # 2. Chi phí thời gian truy xuất
    calc["raw_retrieval"] = (calc["distance"] + gamma) / (duration + 0.1)
    
    # 3. Chi phí cân bằng tải bãi
    calc["occ_rate"] = calc["occ"] / calc["cap"]
    calc["raw_balance"] = calc["occ_rate"] ** 2

    # Chuẩn hóa Min-Max [0, 1]
    def min_max(s):
        s_min, s_max = s.min(), s.max()
        if s_max == s_min:
            return pd.Series(0.0, index=s.index)
        return (s - s_min) / (s_max - s_min)

    tot_w = we + wr + wb
    we_norm = we / tot_w if tot_w > 0 else 1/3
    wr_norm = wr / tot_w if tot_w > 0 else 1/3
    wb_norm = wb / tot_w if tot_w > 0 else 1/3

    calc["norm_energy"] = min_max(calc["raw_energy"])
    calc["norm_retrieval"] = min_max(calc["raw_retrieval"])
    calc["norm_balance"] = min_max(calc["raw_balance"])

    # Tính tổng điểm chi phí (Cost Score)
    calc["score"] = (we_norm * calc["norm_energy"] + wr_norm * calc["norm_retrieval"] + wb_norm * calc["norm_balance"])
    calc.loc[calc["is_full"], "score"] = 999.0
    return calc

res_df = run_selection_algorithm(df_blocks, car_weight, park_duration, w_energy, w_retrieval, w_balance)
valid_blocks = res_df[~res_df["is_full"]]
best_block = valid_blocks.loc[valid_blocks["score"].idxmin()] if not valid_blocks.empty else None

# ---------------------------------------------------------
# 5. HIỂN THỊ METRICS TỔNG QUAN
# ---------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("🎯 Block Thuật Toán Chọn", best_block["id"] if best_block is not None else "Hết chỗ", "Tối ưu nhất")
with m2:
    st.metric("📏 Quãng đường AGV", f"{int(best_block['distance'])} m" if best_block is not None else "N/A")
with m3:
    st.metric("📊 Tỷ lệ lấp đầy", f"{int(best_block['occ_rate']*100)}%" if best_block is not None else "N/A", f"Còn trống {best_block['available']} ô")
with m4:
    st.metric("⚡ Điểm Chi Phí (Cost Score)", f"{best_block['score']:.3f}" if best_block is not None else "N/A")

st.markdown("---")

# ---------------------------------------------------------
# 6. HIỂN THỊ SƠ ĐỒ MẶT BẰNG 2D & BIỂU ĐỒ SO SÁNH
# ---------------------------------------------------------
col_map, col_chart = st.columns([65, 35])

with col_map:
    st.subheader("🗺️ Sơ Đồ Kiến Trúc Mặt Bằng Bãi Đỗ Xe")
    
    fig = go.Figure()

    # 1. Vẽ tường bao bên ngoài bãi đỗ
    fig.add_shape(type="rect", x0=0, y0=0, x1=100, y1=95, line=dict(color="#2c3e50", width=4), fillcolor="#f8f9fa")

    # 2. Vẽ Cổng ENTRANCE (Lối vào/ra)
    fig.add_shape(type="rect", x0=42, y0=-5, x1=58, y1=0, fillcolor="#e74c3c", line=dict(color="black", width=2))
    fig.add_trace(go.Scatter(x=[50], y=[-2.5], mode="text", text=["<b>ENTRANCE (LỐI VÀO)</b>"], textfont=dict(color="white", size=10), showlegend=False))

    # 3. Vẽ Trạm sạc / Trung tâm điều khiển (Góc dưới bên phải)
    fig.add_shape(type="rect", x0=60, y0=2, x1=84, y1=8, fillcolor="#f39c12", line=dict(color="black", width=1))
    fig.add_trace(go.Scatter(x=[72], y=[5], mode="text", text=["TRẠM SẠC & ĐIỀU KHIỂN"], textfont=dict(size=9, color="black"), showlegend=False))

    # 4. Vẽ các Tuyến đường AGV (Đường nét đứt màu xanh)
    agv_lanes = [
        {"x": [13, 13], "y": [6, 91]}, {"x": [87, 87], "y": [6, 91]}, {"x": [50, 50], "y": [0, 53]},
        {"x": [13, 87], "y": [6, 6]}, {"x": [13, 87], "y": [53, 53]}, {"x": [13, 87], "y": [71, 71]}, {"x": [13, 87], "y": [91, 91]}
    ]
    for lane in agv_lanes:
        fig.add_trace(go.Scatter(x=lane["x"], y=lane["y"], mode="lines", line=dict(color="#3498db", width=1.5, dash="dash"), showlegend=False, hoverinfo="none"))

    # 5. Vẽ từng Block theo đúng bản vẽ kỹ thuật
    for _, row in res_df.iterrows():
        is_selected = (best_block is not None) and (row["id"] == best_block["id"])
        
        if row["is_full"]:
            fill_bg = "#bdc3c7"     # Màu xám nếu đầy
            border_col = "#7f8c8d"
            txt_status = "FULL"
        elif is_selected:
            fill_bg = "#2ecc71"     # Màu xanh lá sáng nếu được thuật toán chọn
            border_col = "#1e8449"
            txt_status = "⭐ CHỌN"
        else:
            fill_bg = "#ffffff"     # Màu trắng mặc định
            border_col = "#34495e"
            txt_status = f"Score: {row['score']:.2f}"

        # Vẽ khối hình chữ nhật của Block
        fig.add_shape(
            type="rect",
            x0=row["x0"], y0=row["y0"],
            x1=row["x1"], y1=row["y1"],
            fillcolor=fill_bg,
            line=dict(color=border_col, width=3 if is_selected else 1.5),
            opacity=0.9
        )

        # Hiển thị Tên Block
        fig.add_trace(go.Scatter(
            x=[row["cx"]], y=[row["cy"]],
            mode="text",
            text=[f"<b>{row['id']}</b><br>{txt_status}"],
            textfont=dict(color="black" if not is_selected else "white", size=11 if is_selected else 9),
            hoverinfo="text",
            hovertext=(
                f"<b>{row['id']}</b> ({row['desc']})<br>"
                f"Sức chứa: {row['occ']}/{row['cap']} ô<br>"
                f"Quãng đường: {int(row['distance'])}m<br>"
                f"Điểm Chi Phí: {row['score']:.3f}"
            ),
            showlegend=False
        ))

        # Nếu được chọn -> Vẽ tuyến đường di chuyển màu xanh lá nối từ Cổng đến Block
        if is_selected:
            fig.add_trace(go.Scatter(
                x=[50, 50, row["cx"]],
                y=[0, row["cy"], row["cy"]],
                mode="lines+markers",
                line=dict(color="#27ae60", width=4),
                marker=dict(size=6, color="#27ae60"),
                showlegend=False
            ))

    fig.update_layout(
        xaxis=dict(range=[-3, 103], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[-8, 98], showgrid=False, zeroline=False, visible=False),
        height=540,
        margin=dict(l=5, r=5, t=5, b=5),
        plot_bgcolor="#f4f6f7"
    )
    
    st.plotly_chart(fig, use_container_width=True)

with col_chart:
    st.subheader("📊 So Sánh Điểm Chi Phí")
    
    df_chart = res_df.sort_values(by="score")
    fig_bar = px.bar(
        df_chart,
        x="id",
        y=["norm_energy", "norm_retrieval", "norm_balance"],
        title="Phân Tích Thành Phần Chi Phí",
        labels={"value": "Điểm Chi Phí", "id": "Block", "variable": "Thành phần"},
        color_discrete_map={
            "norm_energy": "#e74c3c",     # Đỏ: Năng lượng
            "norm_retrieval": "#f1c40f",  # Vàng: Thời gian
            "norm_balance": "#9b59b6"     # Tím: Tải bãi
        },
        barmode="stack"
    )
    fig_bar.update_layout(height=540, margin=dict(l=5, r=5, t=35, b=5))
    st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------------
# 7. BẢNG DỮ LIỆU CHI TIẾT
# ---------------------------------------------------------
st.subheader("📋 Bảng So Sánh Chi Tiết Các Block")

disp_df = res_df[["id", "desc", "distance", "occ", "cap", "available", "norm_energy", "norm_retrieval", "norm_balance", "score"]].copy()
disp_df.columns = ["Block", "Vị Trí", "Quãng Đường (m)", "Đã Đỗ", "Sức Chứa", "Ô Trống", "CP Năng Lượng", "CP Thời Gian", "CP Cân Bằng", "Điểm Chi Phí"]

def highlight_best_row(row):
    if best_block is not None and row["Block"] == best_block["id"]:
        return ['background-color: #d4edda; font-weight: bold'] * len(row)
    return [''] * len(row)

st.dataframe(
    disp_df.style.apply(highlight_best_row, axis=1).format({
        "Quãng Đường (m)": "{:.0f}",
        "CP Năng Lượng": "{:.3f}",
        "CP Thời Gian": "{:.3f}",
        "CP Cân Bằng": "{:.3f}",
        "Điểm Chi Phí": "{:.3f}"
    }),
    use_container_width=True
)
