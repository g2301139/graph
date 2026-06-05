import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from io import StringIO
import re

st.set_page_config(page_title="万能グラフ作成アプリ", layout="wide")

st.title("📊 高機能グラフ作成Webアプリ")
st.write("複数軸の描画エラーを完全に修正し、安定して動作するレイアウトを構築しました。")

# -----------------------------------------------------------------------------
# 1. データ入力セクション
# -----------------------------------------------------------------------------
st.header("1. データの入力")

default_paste_data = (
    "X軸データ\t売上\t利益\t目標値\tカテゴリー\n"
    "1\t10\t2\t8\tA\n"
    "2\t12\t5\t10\tB\n"
    "3\t18\t4\t15\tA\n"
    "4\t20\t8\t18\tB\n"
    "5\t26\t7\t22\tA"
)

paste_input = st.text_area(
    "Excelやスプレッドシートからデータをコピーし、下の枠内に貼り付けてください（Ctrl+V）：",
    value=default_paste_data,
    height=180
)

df = pd.DataFrame()

if paste_input.strip():
    try:
        lines = paste_input.strip().split('\n')
        processed_lines = []
        for line in lines:
            if ',' not in line:
                line = re.sub(r'[\t\s ]+', '\t', line)
            processed_lines.append(line)
        
        final_input = '\n'.join(processed_lines)
        sep_char = ',' if ',' in processed_lines[0] else '\t'
        
        df = pd.read_csv(StringIO(final_input), sep=sep_char)
        
        if len(df.columns) == 1:
            df = pd.read_csv(StringIO(final_input), sep=r'\s+', engine='python')

    except Exception as e:
        st.error(f"データの読み込みに失敗しました。エラー: {e}")
        df = pd.DataFrame()

if not df.empty:
    st.subheader("現在のデータ確認")
    st.dataframe(df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# 2. グラフの設定セクション
# -----------------------------------------------------------------------------
if not df.empty:
    st.header("2. グラフの設定")
    columns = df.columns.tolist()

    if len(columns) < 2:
        st.error("データの列が正しく分かれていません。貼り付けるデータの区切りを確認してください。")
    else:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            x_axis = st.selectbox("X軸（横軸）を選択", options=columns, index=0)
        with col2:
            default_y = [c for c in columns if c != x_axis and c != "カテゴリー"]
            if not default_y:
                default_y = [columns[0]]
            y_axes = st.multiselect("グラフに描画するデータ列を選択（複数選択可）", options=columns, default=default_y)
        with col3:
            color_axis = st.selectbox("色分けする列（オプション）", options=["なし"] + columns, index=0)

        # 縦軸（Y軸）の配置設定
        st.subheader("縦軸（Y軸）の配置設定")
        
        axis_names = []
        data_axis_mapping = {}

        if y_axes:
            if len(y_axes) > 1:
                is_integrated = st.checkbox("選択したデータの縦軸（名前）を1つに統合する", value=False)
                
                if is_integrated:
                    integrated_name = st.text_input("統合後の縦軸の名前を入力してください", value="統合された縦軸")
                    axis_names = [integrated_name]
                    for y_col in y_axes:
                        data_axis_mapping[y_col] = {"axis_idx": 0, "axis_name": integrated_name}
                else:
                    axis_names = list(y_axes)
                    for idx, y_col in enumerate(y_axes):
                        data_axis_mapping[y_col] = {"axis_idx": idx, "axis_name": y_col}
            else:
                axis_names = list(y_axes)
                data_axis_mapping[y_axes[0]] = {"axis_idx": 0, "axis_name": y_axes[0]}
        else:
            axis_names = ["縦軸"]

        # 線の引き方
        st.subheader("表示する線の選択")
        col_show1, col_show2 = st.columns(2)
        with col_show1:
            show_trend = st.checkbox("全体の平均を通る一直線（トレンド線）を表示する", value=False)
        with col_show2:
            show_curve = st.checkbox("数値をみて自動判定した線を表示する", value=False)

        # 軸の最大値・最小値
        st.subheader("軸の表示範囲設定")
        custom_range = st.checkbox("手動で軸の最大値・最小値を指定する")
        
        try:
            x_min_def, x_max_def = float(df[x_axis].min()), float(df[x_axis].max())
            y_min_def = float(df[y_axes].min().min()) if y_axes else 0.0
            y_max_def = float(df[y_axes].max().max()) if y_axes else 100.0
        except:
            x_min_def, x_max_def, y_min_def, y_max_def = 0.0, 100.0, 0.0, 100.0

        x_range_input, y_range_input = None, None
        if custom_range:
            cx1, cx2, cy1, cy2 = st.columns(4)
            with cx1: x_min = st.number_input("X軸 最小値", value=x_min_def)
            with cx2: x_max = st.number_input("X軸 最大値", value=x_max_def)
            with cy1: y_min = st.number_input("Y軸 最小値", value=y_min_def)
            with cy2: y_max = st.number_input("Y軸 最大値", value=y_max_def)
            x_range_input = [x_min, x_max]
            y_range_input = [y_min, y_max]

        # -----------------------------------------------------------------------------
        # 3. グラフの描画
        # -----------------------------------------------------------------------------
        st.header("3. 生成されたグラフ")

        if not y_axes:
            st.warning("データ列を1つ以上選択してください。")
        else:
            fig = go.Figure()
            color_cycle = px.colors.qualitative.Plotly
            color_idx = 0

            def get_trendline_data(dataframe, x_col, y_col):
                try:
                    x_vals = pd.to_numeric(dataframe[x_col]).values
                    y_vals = pd.to_numeric(dataframe[y_col]).values
                    idx = np.isfinite(x_vals) & np.isfinite(y_vals)
                    a, b = np.polyfit(x_vals[idx], y_vals[idx], 1)
                    return np.array([min(x_vals), max(x_vals)]), a * np.array([min(x_vals), max(x_vals)]) + b
                except: return None, None

            def determine_shape(dataframe, x, y):
                try:
                    x_val, y_val = pd.to_numeric(dataframe[x]).values, pd.to_numeric(dataframe[y]).values
                    if len(x_val) < 3: return "linear"
                    return "linear" if np.var(np.diff(np.diff(y_val) / np.diff(x_val))) < 1e-5 else "spline"
                except: return "linear"

            # プロット処理
            for y_axis in y_axes:
                mapping = data_axis_mapping.get(y_axis)
                if not mapping: continue
                
                ax_idx = mapping["axis_idx"]
                # Plotlyのマルチ軸指定は 'y', 'y2', 'y3' ... となる
                yaxis_id = "y" if ax_idx == 0 else f"y{ax_idx + 1}"

                if color_axis != "なし":
                    unique_categories = df[color_axis].unique()
                    for cat in unique_categories:
                        assigned_color = color_cycle[color_idx % len(color_cycle)]
                        color_idx += 1
                        sub_df = df[df[color_axis] == cat]
                        
                        fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="markers", marker=dict(size=10, color=assigned_color), name=f"{y_axis} ({cat})", yaxis=yaxis_id))
                        if show_trend:
                            x_t, y_t = get_trendline_data(sub_df, x_axis, y_axis)
                            if x_t is not None: fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=assigned_color, dash="dash"), name=f"{y_axis} ({cat}) [直線]", yaxis=yaxis_id))
                        if show_curve:
                            shape_type = determine_shape(sub_df, x_axis, y_axis)
                            fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="lines", line=dict(shape=shape_type, color=assigned_color), name=f"{y_axis} ({cat}) [各点結び]", yaxis=yaxis_id))
                else:
                    assigned_color = color_cycle[color_idx % len(color_cycle)]
                    color_idx += 1
                    
                    fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="markers", marker=dict(size=10, color=assigned_color), name=y_axis, yaxis=yaxis_id))
                    if show_trend:
                        x_t, y_t = get_trendline_data(df, x_axis, y_axis)
                        if x_t is not None: fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=assigned_color, dash="dash"), name=f"{y_axis} [直線]", yaxis=yaxis_id))
                    if show_curve:
                        shape_type = determine_shape(df, x_axis, y_axis)
                        fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="lines", line=dict(shape=shape_type, color=assigned_color), name=f"{y_axis} [各点結び]", yaxis=yaxis_id))

            # 🛠️【レイアウト設定の修正】
            # X軸の基本設定とドメイン（描画幅）を制限して、右側に複数軸を追加できるようにします
            layout_kwargs = {
                "xaxis": dict(title=x_axis, range=x_range_input, domain=[0.05, 0.85]),
                "hovermode": "closest"
            }

            # 軸の名前や位置設定を、辞書形式で安全に構築
            for i, name in enumerate(axis_names):
                actual_range = y_range_input if custom_range else None
                
                axis_config = dict(
                    title=name,
                    range=actual_range,
                    titlefont=dict(color=color_cycle[i % len(color_cycle)]),
                    tickfont=dict(color=color_cycle[i % len(color_cycle)])
                )
                
                if i == 0:
                    # 主軸（左側）
                    axis_config["side"] = "left"
                else:
                    # 2つ目以降の軸（すべて右側にずらして配置）
                    position_offset = 0.85 + ((i - 1) * 0.07)
                    axis_config.update(dict(
                        overlaying="y",
                        side="right",
                        anchor="free",
                        position=position_offset
                    ))
                
                layout_kwargs[f"yaxis{'' if i == 0 else i + 1}"] = axis_config

            # 一括で更新を適用
            fig.update_layout(**layout_kwargs)

            # 最終描画
            st.plotly_chart(fig, use_container_width=True)

            # -----------------------------------------------------------------------------
            # 4. ファイル保存
            # -----------------------------------------------------------------------------
            st.header("4. データの保存")
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 入力データをCSVで保存", data=csv, file_name="graph_data.csv", mime="text/csv")
