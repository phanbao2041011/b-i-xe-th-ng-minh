import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ---------------------------------------------------------
# 1. CẤU HÌNH TRANG STREAMLIT
# ---------------------------------------------------------
st.set_page_config(
    page_title="Mô phỏng Thuật toán Chọn Block Bãi Đỗ AGV",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Hệ Thống Trực Quan Hóa Thuật Toán Chọn Block Ô Đỗ AGV")
st.markdown("""
*Mô hình hỗ trợ ra quyết định chọn **Tòa/Block ô đỗ xe** tối ưu cho robot AGV dựa trên **Khối lượng xe** và **Thời gian đỗ dự kiến**.*
""")

# ---------------------------------------------------------
# 2. KHỞI TẠO DỮ LIỆU CÁC BLOCK BÃI ĐỖ (Mô phỏng sơ đồ 2D)
# ---------------------------------------------------------
@st.cache_data
def get_initial_blocks():
    # Vị trí cổng nhận/trả xe đặt tại tọa độ (0, 0)
    data = [
        {"block_id": "Block A", "x": 15, "y": 10, "capacity": 30, "occupied": 25, "floors": 3},
        {"block_id": "Block B", "x": 35, "y": 10, "capacity": 30, "occupied": 18, "floors": 3},
        {"block_id": "Block C", "x": 55, "y": 10, "capacity": 30, "occupied": 29, "floors": 3},
        {"block_id": "Block D", "x": 15, "y": 35, "capacity": 30, "occupied": 12, "floors": 3},
        {"block_id": "Block E", "x": 35, "y": 35, "capacity": 30, "occupied": 8,  "floors": 3},
        {"block_id": "Block F", "x": 55, "y": 35, "capacity": 30, "occupied": 30, "floors": 3}, # Full
    ]
    df = pd.DataFrame(data)
    # Tính khoảng cách Euclidean từ Cổng (0,0) đến tâm từng Block
    df["distance"] = np.sqrt(df["x"]**2 + df["y"]**2).round(1)
    return df

blocks_df = get_initial_blocks().copy()

# ---------------------------------------------------------
# 3. SIDEBAR - ĐẦU VÀO DỮ LIỆU KHÁCH HÀNG & THAM SỐ
# ---------------------------------------------------------
st.sidebar.header("📥 1. Thông Tin Xe & Yêu Cầu")

# Kịch bản mẫu nhanh
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
park_duration = st.sidebar.number_input("Thời gian dự kiến đỗ T_park (giờ):", min_value=0.5, max_value=168.0, value=init_time, step=0.5)

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
# 4. HÀM TÍNH TOÁN THUẬT TOÁN (CORE ALGORITHM)
# ---------------------------------------------------------
def run_block_selection_algorithm(df, weight, duration, w_e, w_r, w_b):
    df_calc = df.copy()
    
    # Kiểm tra trạng thái ô còn trống
    df_calc["available_slots"] = df_calc["capacity"] - df_calc["occupied"]
    df_calc["is_full"] = df_calc["available_slots"] <= 0
    
    # Hệ số hằng số vật lý AGV
    alpha = 0.01  # Chi phí di chuyển ngang/m/kg
    beta = 2.0    # Chi phí nâng trung bình 3 tầng
    gamma = 5.0   # Hệ số quy đổi tầng sang khoảng cách
    
    # 1. Chi phí năng lượng raw
    df_calc["raw_energy"] = weight * (alpha * df_calc["distance"] + beta)
    
    # 2. Chi phí thời gian truy xuất raw
    df_calc["raw_retrieval"] = (df_calc["distance"] + gamma) / (duration + 0.1)
    
    # 3. Chi phí cân bằng tải raw (Tỷ lệ lấp đầy bình phương)
    df_calc["occupancy_rate"] = df_calc["occupied"] / df_calc["capacity"]
    df_calc["raw_balance"] = df_calc["occupancy_rate"] ** 2

    # Chuẩn hóa Min-Max các thành phần về dải [0, 1] để kết hợp trọng số
    def min_max(series):
        s_min, s_max = series.min(), series.max()
        if s_max == s_min:
            return pd.Series(0.0, index=series.index)
        return (series - s_min) / (s_max - s_min)

    df_calc["norm_energy"] = min_max(df_calc["raw_energy"])
    df_calc["norm_retrieval"] = min_max(df_calc["raw_retrieval"])
    df_calc["norm_balance"] = min_max(df_calc["raw_balance"])

    # Tính Tổng Điểm Chi Phí (Cost Score)
    df_calc["total_score"] = (
        w_e * df_calc["norm_energy"] +
        w_r * df_calc["norm_retrieval"] +
        w_b * df_calc["norm_balance"]
    )
    
    # Đặt chi phí vô cùng cho các Block đã đầy
    df_calc.loc[df_calc["is_full"], "total_score"] = 999.0

    return df_calc

result_df = run_block_selection_algorithm(
    blocks_df, car_weight, park_duration, 
    w_energy_norm, w_retrieval_norm, w_balance_norm
)

# Tìm Block được khuyến nghị (Score nhỏ nhất và không đầy)
valid_blocks = result_df[~result_df["is_full"]]
best_block = valid_blocks.loc[valid_blocks["total_score"].idxmin()] if not valid_blocks.empty else None

# ---------------------------------------------------------
# 5. HIỂN THỊ KẾT QUẢ NỔI BẬT (METRICS)
# ---------------------------------------------------------
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric(
        label="🎯 Block Được Chọn Tối Ưu",
        value=best_block["block_id"] if best_block is not None else "Hết chỗ",
        delta="Khuyên dùng" if best_block is not None else "Cảnh báo"
    )
with col_m2:
    st.metric(
        label="📏 Khoảng Cách Đến Cổng",
        value=f"{best_block['distance']} m" if best_block is not None else "N/A"
    )
with col_m3:
    st.metric(
        label="📊 Tỷ Lệ Lấp Đầy Block",
        value=f"{int(best_block['occupancy_rate']*100)}%" if best_block is not None else "N/A",
        delta=f"Còn trống {best_block['available_slots']} ô" if best_block is not None else "0 ô"
    )
with col_m4:
    st.metric(
        label="⚡ Điểm Chi Phí (Cost Score)",
        value=f"{best_block['total_score']:.3f}" if best_block is not None else "N/A",
        help="Điểm càng thấp càng tối ưu"
    )

st.markdown("---")

# ---------------------------------------------------------
# 6. TRỰC QUAN HÓA SƠ ĐỒ BÃI ĐỖ (PLOTLY 2D MAP)
# ---------------------------------------------------------
left_col, right_col = st.columns([6, 4])

with left_col:
    st.subheader("🗺️ Sơ Đồ Trực Quan Vị Trí Các Block")
    
    fig = go.Figure()

    # 1. Vẽ Cổng Nhận/Trả Xe (Gate) tại (0, 0)
    fig.add_trace(go.Scatter(
        x=[0], y=[0],
        mode="markers+text",
        marker=dict(size=24, color="red", symbol="star"),
        name="Cổng Ra/Vào",
        text=["🚪 CỔNG RA/VÀO"],
        textposition="top center"
    ))

    # 2. Vẽ các Block ô đỗ
    for _, row in result_df.iterrows():
        is_selected = (best_block is not None) and (row["block_id"] == best_block["block_id"])
        
        # Thiết lập màu sắc và kích thước marker
        if row["is_full"]:
            color = "#7f8c8d"  # Xám nếu đầy
            status_text = "ĐÃ ĐẦY"
        elif is_selected:
            color = "#2ecc71"  # Xanh lá sáng nếu được chọn
            status_text = "⭐ ĐƯỢC CHỌN"
        else:
            color = "#3498db"  # Xanh dương mặc định
            status_text = f"Điểm: {row['total_score']:.2f}"

        # Vẽ hình khối Block
        fig.add_trace(go.Scatter(
            x=[row["x"]], y=[row["y"]],
            mode="markers+text",
            marker=dict(
                size=45 if is_selected else 35,
                color=color,
                symbol="square",
                line=dict(width=3 if is_selected else 1, color="black")
            ),
            name=row["block_id"],
            text=[f"<b>{row['block_id']}</b><br>{status_text}"],
            textposition="middle center",
            hoverinfo="text",
            hovertext=(
                f"<b>{row['block_id']}</b><br>"
                f"Khoảng cách: {row['distance']}m<br>"
                f"Đã đỗ: {row['occupied']}/{row['capacity']} ô ({int(row['occupancy_rate']*100)}%)<br>"
                f"Điểm Chi Phí Tổng: {row['total_score']:.3f}"
            )
        ))

        # Đường nối từ cổng đến Block được chọn
        if is_selected:
            fig.add_trace(go.Scatter(
                x=[0, row["x"]], y=[0, row["y"]],
                mode="lines",
                line=dict(color="#2ecc71", width=3, dash="dash"),
                showlegend=False
            ))

    fig.update_layout(
        xaxis=dict(title="Tọa độ X (m)", range=[-5, 70]),
        yaxis=dict(title="Tọa độ Y (m)", range=[-5, 50]),
        height=450,
        margin=dict(l=20, r=20, t=30, b=20),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

with right_col:
    st.subheader("📊 So Sánh Điểm Chi Phí Giữa Các Block")
    
    # Biểu đồ cột phân tích chi phí
    df_chart = result_df.sort_values(by="total_score")
    
    fig_bar = px.bar(
        df_chart,
        x="block_id",
        y=["norm_energy", "norm_retrieval", "norm_balance"],
        title="Phân Tích Thành Phần Chi Phí (Chuẩn Hóa)",
        labels={"value": "Điểm Thành Phần (0 - 1)", "block_id": "Tòa / Block", "variable": "Thành phần"},
        color_discrete_map={
            "norm_energy": "#e74c3c",     # Đỏ: Năng lượng
            "norm_retrieval": "#f1c40f",  # Vàng: Thời gian truy xuất
            "norm_balance": "#9b59b6"     # Tím: Cân bằng tải
        },
        barmode="stack"
    )
    fig_bar.update_layout(height=450, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------------
# 7. BẢNG DỮ LIỆU CHI TIẾT & GIẢI THÍCH LÝ DO
# ---------------------------------------------------------
st.subheader("📋 Bảng Số Liệu Chi Tiết Đánh Giá Thuật Toán")

# Format hiển thị dataframe đẹp mắt
display_df = result_df[[
    "block_id", "distance", "occupied", "capacity", "available_slots",
    "norm_energy", "norm_retrieval", "norm_balance", "total_score"
]].copy()

display_df.columns = [
    "Block", "Khoảng Cách (m)", "Đã Đỗ", "Tổng Ô", "Ô Trống",
    "CP Năng Lượng", "CP Trả Xe", "CP Cân Bằng", "Tổng Điểm Chi Phí"
]

# Highlight dòng được chọn
def highlight_best(row):
    if best_block is not None and row["Block"] == best_block["block_id"]:
        return ['background-color: #d4edda; font-weight: bold'] * len(row)
    return [''] * len(row)

st.dataframe(
    display_df.style.apply(highlight_best, axis=1).format({
        "Khoảng Cách (m)": "{:.1f}",
        "CP Năng Lượng": "{:.3f}",
        "CP Trả Xe": "{:.3f}",
        "CP Cân Bằng": "{:.3f}",
        "Tổng Điểm Chi Phí": "{:.3f}"
    }),
    use_container_width=True
)

# 💡 Giải thích quyết định của thuật toán
if best_block is not None:
    st.info(f"""
    💡 **Giải thích lý do thuật toán chọn {best_block['block_id']}:**
    * **Khối lượng xe:** {car_weight} kg | **Thời gian đỗ:** {park_duration} giờ.
    * **Năng lượng tiêu thụ:** Block cách cổng {best_block['distance']}m, tối ưu công di chuyển ngang của AGV.
    * **Thời gian đáp ứng:** Đáp ứng tốt chu kỳ lấy xe dự kiến {park_duration}h.
    * **Tải trọng bãi:** Block hiện mới lấp đầy {int(best_block['occupancy_rate']*100)}%, tránh hiện tượng tắc nghẽn giao thông AGV.
    """)
