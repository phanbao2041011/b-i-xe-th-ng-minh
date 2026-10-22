import streamlit as st
import pandas as pd
import numpy as np

# Kiểm tra thư viện Plotly
try:
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# ---------------------------------------------------------
# 1. CẤU HÌNH TRANG STREAMLIT
# ---------------------------------------------------------
st.set_page_config(
    page_title="Mô Phỏng Sơ Đồ Chọn Block Đỗ Xe AGV",
    page_icon="🚘",
    layout="wide"
)

st.title("🚘 Mô Phỏng Sơ Đồ Chọn Block Đỗ Xe AGV")
st.markdown("Hệ thống tự động tính toán **Block đỗ xe tối ưu** dựa trên **Trọng lượng xe** và **Thời gian đỗ** trực tiếp trên sơ đồ mặt bằng.")

if not HAS_PLOTLY:
    st.error("⚠️ Thiếu thư viện 'plotly'! Hãy kiểm tra file requirements.txt trên GitHub và thêm dòng 'plotly' vào.")
    st.stop()

try:
    # ---------------------------------------------------------
    # 2. KHỞI TẠO TỌA ĐỘ BLOCK (CAD LAYOUT 9 BLOCK)
    # ---------------------------------------------------------
    @st.cache_data
    def get_map_data():
        blocks = [
            {"id": "Block 8", "x0": 3,  "x1": 11, "y0": 12, "y1": 88, "cx": 7,  "cy": 50, "cap": 48, "occ": 25, "desc": "Dãy dọc Trái"},
            {"id": "Block 9", "x0": 89, "x1": 97, "y0": 12, "y1": 88, "cx": 93, "cy": 50, "cap": 48, "occ": 42, "desc": "Dãy dọc Phải"},
            {"id": "Block 1", "x0": 17, "x1": 29, "y0": 12, "y1": 38, "cx": 23, "cy": 25, "cap": 24, "occ": 18, "desc": "Khu Trung tâm 1"},
            {"id": "Block 2", "x0": 33, "x1": 45, "y0": 12, "y1": 38, "cx": 39, "cy": 25, "cap": 24, "occ": 12, "desc": "Khu Trung tâm 2"},
            {"id": "Block 3", "x0": 55, "x1": 67, "y0": 12, "y1": 38, "cx": 61, "cy": 25, "cap": 24, "occ": 21, "desc": "Khu Trung tâm 3"},
            {"id": "Block 4", "x0": 71, "x1": 83, "y0": 12, "y1": 38, "cx": 77, "cy": 25, "cap": 24, "occ": 10, "desc": "Khu Trung tâm 4"},
            {"id": "Block 7", "x0": 55, "x1": 83, "y0": 42, "y1": 50, "cx": 69, "cy": 46, "cap": 30, "occ": 30, "desc": "Dãy ngang nhỏ (Đầy)"},
            {"id": "Block 6", "x0": 17, "x1": 83, "y0": 56, "y1": 68, "cx": 50, "cy": 62, "cap": 60, "occ": 38, "desc": "Dãy ngang giữa"},
            {"id": "Block 5", "x0": 17, "x1": 83, "y0": 74, "y1": 86, "cx": 50, "cy": 80, "cap": 60, "occ": 54, "desc": "Dãy ngang trên"},
        ]
        df = pd.DataFrame(blocks)
        entrance_x, entrance_y = 50, 0
        df["distance"] = (np.abs(df["cx"] - entrance_x) + np.abs(df["cy"] - entrance_y)).astype(float)
        return df

    df_blocks = get_map_data().copy()

    # ---------------------------------------------------------
    # 3. SIDEBAR INPUTS
    # ---------------------------------------------------------
    st.sidebar.header("📥 Dữ Liệu Xe Nhập Bãi")

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

    tot_w = w_energy + w_retrieval + w_balance
    w_e, w_r, w_b = (w_energy/tot_w, w_retrieval/tot_w, w_balance/tot_w) if tot_w > 0 else (1/3, 1/3, 1/3)

    # ---------------------------------------------------------
    # 4. HÀM TÍNH TOÁN THUẬT TOÁN
    # ---------------------------------------------------------
    def calculate_optimal_block(df, weight, duration, we, wr, wb):
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

        calc["norm_energy"] = min_max(calc["raw_energy"])
        calc["norm_retrieval"] = min_max(calc["raw_retrieval"])
        calc["norm_balance"] = min_max(calc["raw_balance"])

        calc["score"] = (we * calc["norm_energy"] + wr * calc["norm_retrieval"] + wb * calc["norm_balance"])
        calc.loc[calc["is_full"], "score"] = 999.0
        return calc

    res_df = calculate_optimal_block(df_blocks, car_weight, park_duration, w_e, w_r, w_b)
    valid = res_df[~res_df["is_full"]]
    best = valid.loc[valid["score"].idxmin()] if not valid.empty else None

    # ---------------------------------------------------------
    # 5. METRICS
    # ---------------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("🎯 Block Được Chọn", best["id"] if best is not None else "Hết chỗ", "Tối ưu nhất")
    with m2:
        st.metric("📏 Quãng đường AGV", f"{int(best['distance'])} m" if best is not None else "N/A")
    with m3:
        st.metric("📊 Tỷ lệ lấp đầy", f"{int(best['occ_rate']*100)}%" if best is not None else "N/A", f"Còn trống {best['available']} ô")
    with m4:
        st.metric("⚡ Điểm Chi Phí", f"{best['score']:.3f}" if best is not None else "N/A")

    st.markdown("---")

    # ---------------------------------------------------------
    # 6. SƠ ĐỒ MẶT BẰNG 2D
    # ---------------------------------------------------------
    c_left, c_right = st.columns([65, 35])

    with c_left:
        st.subheader("🗺️ Sơ Đồ Kiến Trúc Mặt Bằng Bãi Đỗ Xe")
        
        fig = go.Figure()
        fig.add_shape(type="rect", x0=0, y0=0, x1=100, y1=95, line=dict(color="#2c3e50", width=4), fillcolor="#f8f9fa")
        fig.add_shape(type="rect", x0=42, y0=-4, x1=58, y1=0, fillcolor="#e74c3c", line=dict(color="black", width=2))
        fig.add_trace(go.Scatter(x=[50], y=[-2], mode="text", text=["<b>LỐI VÀO / RA</b>"], textfont=dict(color="white", size=10), showlegend=False))

        agv_lanes = [
            {"x": [13, 13], "y": [6, 91]}, {"x": [86, 86], "y": [6, 91]}, {"x": [50, 50], "y": [0, 53]},
            {"x": [13, 86], "y": [6, 6]}, {"x": [13, 86], "y": [53, 53]}, {"x": [13, 86], "y": [71, 71]}, {"x": [13, 86], "y": [91, 91]}
        ]
        for lane in agv_lanes:
            fig.add_trace(go.Scatter(x=lane["x"], y=lane["y"], mode="lines", line=dict(color="#3498db", width=1.5, dash="dash"), showlegend=False, hoverinfo="none"))

        for _, row in res_df.iterrows():
            is_selected = (best is not None) and (row["id"] == best["id"])
            if row["is_full"]:
                fill_bg, border_col, txt_status = "#bdc3c7", "#7f8c8d", "FULL"
            elif is_selected:
                fill_bg, border_col, txt_status = "#2ecc71", "#1e8449", "⭐ CHỌN"
            else:
                fill_bg, border_col, txt_status = "#ffffff", "#34495e", f"Score: {row['score']:.2f}"

            fig.add_shape(
                type="rect", x0=row["x0"], y0=row["y0"], x1=row["x1"], y1=row["y1"],
                fillcolor=fill_bg, line=dict(color=border_col, width=3 if is_selected else 1.5), opacity=0.9
            )
            fig.add_trace(go.Scatter(
                x=[row["cx"]], y=[row["cy"]], mode="text",
                text=[f"<b>{row['id']}</b><br>{txt_status}"],
                textfont=dict(color="black" if not is_selected else "white", size=11 if is_selected else 9),
                hoverinfo="text",
                hovertext=f"<b>{row['id']}</b><br>Quãng đường: {int(row['distance'])}m<br>Score: {row['score']:.3f}",
                showlegend=False
            ))

            if is_selected:
                fig.add_trace(go.Scatter(
                    x=[50, 50, row["cx"]], y=[0, row["cy"], row["cy"]],
                    mode="lines+markers", line=dict(color="#27ae60", width=4),
                    marker=dict(size=6, color="#27ae60"), showlegend=False
                ))

        fig.update_layout(
            xaxis=dict(range=[-3, 103], showgrid=False, visible=False),
            yaxis=dict(range=[-8, 98], showgrid=False, visible=False),
            height=540, margin=dict(l=5, r=5, t=5, b=5), plot_bgcolor="#f4f6f7"
        )
        st.plotly_chart(fig, use_container_width=True)

    with c_right:
        st.subheader("📊 So Sánh Chi Phí")
        df_chart = res_df.sort_values(by="score")
        fig_bar = px.bar(
            df_chart, x="id", y=["norm_energy", "norm_retrieval", "norm_balance"],
            labels={"value": "Điểm", "id": "Block", "variable": "Thành phần"},
            color_discrete_map={"norm_energy": "#e74c3c", "norm_retrieval": "#f1c40f", "norm_balance": "#9b59b6"},
            barmode="stack"
        )
        fig_bar.update_layout(height=540, margin=dict(l=5, r=5, t=35, b=5))
        st.plotly_chart(fig_bar, use_container_width=True)

    # ---------------------------------------------------------
    # 7. BẢNG CHI TIẾT
    # ---------------------------------------------------------
    st.subheader("📋 Bảng So Sánh Chi Tiết")
    disp_df = res_df[["id", "desc", "distance", "occ", "cap", "available", "norm_energy", "norm_retrieval", "norm_balance", "score"]].copy()
    disp_df.columns = ["Block", "Vị Trí", "Quãng Đường (m)", "Đã Đỗ", "Sức Chứa", "Ô Trống", "CP Năng Lượng", "CP Thời Gian", "CP Cân Bằng", "Điểm Chi Phí"]

    def highlight_best_row(row):
        return ['background-color: #d4edda; font-weight: bold'] * len(row) if (best is not None and row["Block"] == best["id"]) else [''] * len(row)

    st.dataframe(disp_df.style.apply(highlight_best_row, axis=1).format({
        "Quãng Đường (m)": "{:.0f}", "CP Năng Lượng": "{:.3f}", "CP Thời Gian": "{:.3f}", "CP Cân Bằng": "{:.3f}", "Điểm Chi Phí": "{:.3f}"
    }), use_container_width=True)

except Exception as err:
    st.error(f"❌ Phát hiện lỗi trong quá trình thực thi: {err}")
