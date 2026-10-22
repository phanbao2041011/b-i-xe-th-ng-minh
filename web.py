import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ---------------------------------------------------------
# 1. CẤU HÌNH TRANG STREAMLIT
# ---------------------------------------------------------
st.set_page_config(
    page_title="Hệ thống chọn Block Bãi đỗ xe AGV",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Hệ Thống Trực Quan Hóa Chọn Block Bãi Đỗ AGV")
st.markdown("""
*Mô hình tối ưu hóa lựa chọn **Block đỗ xe** cho hệ thống Robot AGV dựa trên sơ đồ mặt bằng thực tế 9 Block.*
""")

# ---------------------------------------------------------
# 2. KHỞI TẠO DỮ LIỆU 9 BLOCK THEO BẢN VẼ
# ---------------------------------------------------------
@st.cache_data
def get_initial_blocks():
    """
    Tọa độ (x, y) được chuẩn hóa theo bản vẽ kỹ thuật:
    - Entrance nằm ở đáy trung tâm: (50, 0)
    - Block 1, 2, 3, 4: Cụm trung tâm phía dưới
    - Block 5, 6, 7: Các dãy nằm ngang phía trên
    - Block 8, 9: Hai dãy dọc hai bên cánh (Trái / Phải)
    """
    entrance_x, entrance_y = 50, 0
    
    data = [
        # Block 1 - 4: Dãy trung tâm dưới
        {"block_id": "Block 1", "x": 25, "y": 20, "capacity": 24, "occupied": 18, "type": "Khu trung tâm"},
        {"block_id": "Block 2", "x": 40, "y": 20, "capacity": 24, "occupied": 10, "type": "Khu trung tâm"},
        {"block_id": "Block 3", "x": 60, "y": 20, "capacity": 24, "occupied": 20, "type": "Khu trung tâm"},
        {"block_id": "Block 4", "x": 75, "y": 20, "capacity": 24, "occupied": 8,  "type": "Khu trung tâm"},
        
        # Block 5 - 7: Dãy ngang lớn phía trên
        {"block_id": "Block 5", "x": 50, "y": 80, "capacity": 60, "occupied": 52, "type": "Dãy ngang trên"},
        {"block_id": "Block 6", "x": 50, "y": 60, "capacity": 60, "occupied": 35, "type": "Dãy ngang giữa"},
        {"block_id": "Block 7", "x": 65, "y": 42, "capacity": 30, "occupied": 30, "type": "Dãy ngang dưới"}, # Giả lập full
        
        # Block 8 & 9: Hai dãy dọc cánh trái / cánh phải
        {"block_id": "Block 8", "x": 8,  "y": 50, "capacity": 48, "occupied": 22, "type": "Dãy dọc Trái"},
        {"block_id": "Block 9", "x": 92, "y": 50, "capacity": 48, "occupied": 40, "type": "Dãy dọc Phải"},
    ]
    
    df = pd.DataFrame(data)
    
    # Tính khoảng cách Manhattan theo lối đi AGV từ Entrance (50, 0)
    df["distance"] = (np.abs(df["x"] - entrance_x) + np.abs(df["y"] - entrance_y)).astype(float)
    return df

blocks_df = get_initial_blocks().copy()

# ---------------------------------------------------------
# 3. SIDEBAR - ĐẦU VÀO DỮ LIỆU & TRỌNG SỐ
# ---------------------------------------------------------
st.sidebar.header("📥 1. Thông Tin Xe Nhập Bãi")

scenario = st.sidebar.selectbox(
    "Chọn kịch bản nhanh:",
    ["Tùy chỉnh", "Xe điện nặng - Đỗ ngắn hạn (1h)", "Xe SUV trung bình - Đỗ trong ngày (5h)", "Xe Sedan nhẹ - Đỗ dài hạn (48h)"]
)

if scenario == "Xe điện nặng - Đỗ ngắn hạn (1h)":
    init_weight, init_time = 2800, 1.0
elif scenario == "Xe SUV trung bình - Đỗ trong ngày (5h)":
    init_weight, init_time = 2000, 5.0
elif scenario == "Xe Sedan nhẹ - Đỗ dài hạn (48h)":
    init_weight, init_time = 1300, 48.0
else:
    init_weight, init_time = 1800, 2.5

car_weight = st.sidebar.number_input("Khối lượng xe W_car (kg):", min_value=800, max_value=4000, value=init_weight, step=100)
park_duration = st.sidebar.number_input("Thời gian đỗ dự kiến T_park (giờ):", min_value=0.5, max_value=168.0, value=init_time, step=0.5)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 2. Trọng Số Thuật Toán")
w_energy = st.sidebar.slider("Ưu tiên Năng lượng AGV (w_energy):", 0.0, 1.0, 0.45, 0.05)
w_retrieval = st.sidebar.slider("Ưu tiên Thời gian trả xe (w_retrieval):", 0.0, 1.0, 0.35, 0.05)
w_balance = st.sidebar.slider("Ưu tiên Cân bằng tải bãi (w_balance):", 0.0, 1.0, 0.20, 0.05)

# Chuẩn hóa tổng trọng số = 1
total_w = w_energy + w_retrieval + w_balance
if total_w > 0:
    w_energy_norm = w_energy / total_w
    w_retrieval_norm = w_retrieval / total_w
    w_balance_norm = w_balance / total_w
else:
    w_energy_norm = w_retrieval_norm = w_balance_norm = 1/3

# ---------------------------------------------------------
# 4. HÀM TÍNH TOÁN THUẬT TOÁN ĐÁNH GIÁ BLOCK
# ---------------------------------------------------------
def evaluate_blocks(df, weight, duration, w_e, w_r, w_b):
    df_calc = df.copy()
    
    df_calc["available_slots"] = df_calc["capacity"] - df_calc["occupied"]
    df_calc["is_full"] = df_calc["available_slots"] <= 0
    
    alpha = 0.01  # Chi phí di chuyển ngang/m/kg
    beta = 3.0    # Chi phí trung bình nâng hạ 3 tầng
    gamma = 4.0   # Quy đổi độ phức tạp tuyến đường AGV
    
    # 1. Chi phí năng lượng raw
    df_calc["raw_energy"] = weight * (alpha * df_calc["distance"] + beta)
    
    # 2. Chi phí thời gian truy xuất raw
    df_calc["raw_retrieval"] = (df_calc["distance"] + gamma) / (duration + 0.1)
    
    # 3. Chi phí cân bằng tải raw
    df_calc["occupancy_rate"] = df_calc["occupied"] / df_calc["capacity"]
    df_calc["raw_balance"] = df_calc["occupancy_rate"] ** 2

    # Chuẩn hóa Min-Max [0, 1]
    def min_max(series):
        s_min, s_max = series.min(), series.max()
        if s_max == s_min:
            return pd.Series(0.0, index=series.index)
        return (series - s_min) / (s_max - s_min)

    df_calc["norm_energy"] = min_max(df_calc["raw_energy"])
    df_calc["norm_retrieval"] = min_max(df_calc["raw_retrieval"])
    df_calc["norm_balance"] = min_max(df_calc["raw_balance"])

    # Tổng điểm chi phí (Score)
    df_calc["total_score"] = (
        w_e * df_calc["norm_energy"] +
        w_r * df_calc["norm_retrieval"] +
        w_b * df_calc["norm_balance"]
    )
    
    df_calc.loc[df_calc["is_full"], "total_score"] = 999.0
    return df_calc

result_df = evaluate_blocks(
    blocks_df, car_weight, park_duration, 
    w_energy_norm, w_retrieval_norm, w_balance_norm
)

valid_blocks = result_df[~result_df["is_full"]]
best_block = valid_blocks.loc[valid_blocks["total_score"].idxmin()] if not valid_blocks.empty else None

# ---------------------------------------------------------
# 5. HIỂN THỊ KẾT QUẢ METRICS
# ---------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("🎯 Block Được Chọn", best_block["block_id"] if best_block is not None else "Hết chỗ", "Tối ưu nhất")
with c2:
    st.metric("📏 Quãng đường AGV", f"{int(best_block['distance'])} m" if best_block is not None else "N/A")
with c3:
    st.metric("📊 Tải trọng Block", f"{int(best_block['occupancy_rate']*100)}%" if best_block is not None else "N/A", f"Còn trống {best_block['available_slots']} ô")
with c4:
    st.metric("⚡ Điểm Chi Phí", f"{best_block['total_score']:.3f}" if best_block is not None else "N/A")

st.markdown("---")

# ---------------------------------------------------------
# 6. MÔ PHỎNG SƠ ĐỒ MẶT BẰNG 2D (PLOTLY MAP)
# ---------------------------------------------------------
col_left, col_right = st.columns([6, 4])

with col_left:
    st.subheader("🗺️ Sơ Đồ Mặt Bằng 9 Block Bãi Đỗ Xe")
    
    fig = go.Figure()

    # Entrance (Cổng vào/ra)
    fig.add_trace(go.Scatter(
        x=[50], y=[0],
        mode="markers+text",
        marker=dict(size=22, color="red", symbol="star"),
        text=["🚪 ENTRANCE (LỐI VÀO/RA)"],
        textposition="bottom center",
        name="Cổng Ra/Vào"
    ))

    # Vẽ các Block ô đỗ
    for _, row in result_df.iterrows():
        is_selected = (best_block is not None) and (row["block_id"] == best_block["block_id"])
        
        if row["is_full"]:
            color = "#7f8c8d"
            status = "ĐÃ ĐẦY"
        elif is_selected:
            color = "#2ecc71"
            status = "⭐ ĐƯỢC CHỌN"
        else:
            color = "#3498db"
            status = f"Score: {row['total_score']:.2f}"

        # Chọn shape theo kiểu Block (Dọc / Ngang)
        symbol = "square"
        size = 36 if "Dãy ngang" in row["type"] or "Dãy dọc" in row["type"] else 30
        if is_selected:
            size += 10

        fig.add_trace(go.Scatter(
            x=[row["x"]], y=[row["y"]],
            mode="markers+text",
            marker=dict(
                size=size,
                color=color,
                symbol=symbol,
                line=dict(width=3 if is_selected else 1, color="black")
            ),
            text=[f"<b>{row['block_id']}</b><br>{status}"],
            textposition="middle center",
            hoverinfo="text",
            hovertext=(
                f"<b>{row['block_id']}</b> ({row['type']})<br>"
                f"Quãng đường: {int(row['distance'])}m<br>"
                f"Đã đỗ: {row['occupied']}/{row['capacity']} ô ({int(row['occupancy_rate']*100)}%)<br>"
                f"Điểm Chi Phí: {row['total_score']:.3f}"
            )
        ))

        # Tuyến đường chỉ dẫn đường đi AGV tới Block chọn
        if is_selected:
            # Đường từ Entrance (50, 0) -> Giao điểm ngang -> Block
            fig.add_trace(go.Scatter(
                x=[50, 50, row["x"]],
                y=[0, row["y"], row["y"]],
                mode="lines",
                line=dict(color="#2ecc71", width=3, dash="dash"),
                showlegend=False
            ))

    fig.update_layout(
        xaxis=dict(title="Chiều rộng bãi đỗ (m)", range=[-5, 105], showgrid=True),
        yaxis=dict(title="Chiều sâu bãi đỗ (m)", range=[-10, 95], showgrid=True),
        height=500,
        margin=dict(l=10, r=10, t=20, b=10),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("📊 Phân Tích Chi Phí Theo Block")
    
    df_chart = result_df.sort_values(by="total_score")
    
    fig_bar = px.bar(
        df_chart,
        x="block_id",
        y=["norm_energy", "norm_retrieval", "norm_balance"],
        title="Thành phần Chi Phí (Đã chuẩn hóa)",
        labels={"value": "Điểm Chi Phí", "block_id": "Block", "variable": "Thành phần"},
        color_discrete_map={
            "norm_energy": "#e74c3c",
            "norm_retrieval": "#f1c40f",
            "norm_balance": "#9b59b6"
        },
        barmode="stack"
    )
    fig_bar.update_layout(height=500, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------------
# 7. BẢNG DỮ LIỆU BÁO CÁO CHI TIẾT
# ---------------------------------------------------------
st.subheader("📋 Bảng So Sánh Chi Tiết Tất Cả Các Block")

display_df = result_df[[
    "block_id", "type", "distance", "occupied", "capacity", "available_slots",
    "norm_energy", "norm_retrieval", "norm_balance", "total_score"
]].copy()

display_df.columns = [
    "Block", "Vị Trí Khu Vực", "Khoảng Cách (m)", "Đã Đỗ", "Sức Chứa", "Ô Trống",
    "CP Năng Lượng", "CP Trả Xe", "CP Cân Bằng", "Điểm Chi Phí Tổng"
]

def highlight_selected(row):
    if best_block is not None and row["Block"] == best_block["block_id"]:
        return ['background-color: #d4edda; font-weight: bold'] * len(row)
    return [''] * len(row)

st.dataframe(
    display_df.style.apply(highlight_selected, axis=1).format({
        "Khoảng Cách (m)": "{:.0f}",
        "CP Năng Lượng": "{:.3f}",
        "CP Trả Xe": "{:.3f}",
        "CP Cân Bằng": "{:.3f}",
        "Điểm Chi Phí Tổng": "{:.3f}"
    }),
    use_container_width=True
)

if best_block is not None:
    st.info(f"""
    💡 **Lý do hệ thống chọn {best_block['block_id']}:**
    * **Khối lượng xe:** {car_weight} kg $\rightarrow$ Được ưu tiên phân bổ vào {best_block['type']} cách cổng {int(best_block['distance'])}m để tối ưu công di chuyển của AGV.
    * **Thời gian gửi xe:** {park_duration} giờ $\rightarrow$ Đảm bảo tốc độ đáp ứng trả xe khi hết hạn đỗ.
    * **Cân bằng tải:** Block hiện còn trống **{best_block['available_slots']} ô**, giúp tránh ùn tắc luồng di chuyển AGV.
    """)
