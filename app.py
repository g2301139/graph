import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from io import StringIO
import re

st.set_page_config(page_title="万能グラフ作成アプリ", layout="wide")

st.title("📊 高機能グラフ作成Webアプリ")
st.write("右側の凡例名（データ点の説明）を自由にカスタマイズできるようになりました。")

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

        # 縦軸（Y軸）の配置・統合設定
        st.subheader("縦軸（Y軸）の配置設定")
        
        axis_names = []
        data_axis_mapping = {}
        is_integrated = False

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

        # データごとの線の引き方 & 凡例名の個別カスタム設定
        st.subheader("表示する線と凡例名（右側の名前）の設定")
        line_styles_config = {}
        legend_names_config = {}
        
        if y_axes:
            for y_col in y_axes:
                st.markdown(f"**■ {y_col} の個別設定**")
                style_col, name_col = st.columns(2)
                
                with style_col:
                    line_style = st.selectbox(
                        f"「{y_col}」の線の引き方",
                        options=["マーカーのみ（線なし）", "数値を自動判定した線（曲線）", "全体の平均を通る一直線（トレンド線）"],
                        index=1,
                        key=f"style_{y_col}"
                    )
                    line_styles_config[y_col] = line_style
                
                with name_col:
                    if color_axis != "なし":
                        unique_categories = df[color_axis].unique()
                        for cat in unique_categories:
                            default_legend_name = f"{y_col} ({cat})"
                            custom_legend_name = st.text_input(
                                f"右側に表示する名前: {default_legend_name}", 
                                value=default_legend_name, 
                                key=f"legname_{y_col}_{cat}"
                            )
                            legend_names_config[f"{y_col}_{cat}"] = custom_legend_name
                    else:
                        default_legend_name = y_col
                        custom_legend_name = st.text_input(
                            f"右側に表示する名前: {default_legend_name}", 
                            value=default_legend_name, 
                            key=f"legname_{y_col}"
                        )
                        legend_names_config[y_col] = custom_legend_name

        # 軸の最大値・最小値設定
        st.subheader("軸の表示範囲設定")
        custom_range = st.checkbox("手動で軸の最大値・最小値を指定する")
        
        try:
            x_min_def, x_max_def = float(df[x_axis].min()), float(df[x_axis].max())
        except:
            x_min_def, x_max_def = 0.0, 100.0

        x_range_input = None
        y_ranges_config = {}

        if custom_range:
            cx1, cx2 = st.columns(2)
            with cx1: x_min = st.number_input("X軸 最小値", value=x_min_def)
            with cx2: x_max = st.number_input("X軸 最大値", value=x_max_def)
            x_range_input = [x_min, x_max]
            
            st.write("▼ Y軸の範囲設定")
            for i, name in enumerate(axis_names):
                st.markdown(f"**{name}** の範囲")
                cy1, cy2 = st.columns(2)
                
                try:
                    if is_integrated:
                        y_min_def = float(df[y_axes].min().min())
                        y_max_def = float(df[y_axes].max().max())
                    else:
                        y_min_def = float(df[name].min())
                        y_max_def = float(df[name].max())
                except:
                    y_min_def, y_max_def = 0.0, 100.0
                
                with cy1: y_min = st.number_input(f"最小値 ({name})", value=y_min_def, key=f"ymin_{i}")
                with cy2: y_max = st.number_input(f"最大値 ({name})", value=y_max_def, key=f"ymax_{i}")
                y_ranges_config[i] = [y_min, y_max]

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
                yaxis_id = "y" if ax_idx == 0 else f"y{ax_idx + 1}"
                selected_style = line_styles_config.get(y_axis, "数値を自動判定した線（曲線）")

                if color_axis != "なし":
                    unique_categories = df[color_axis].unique()
                    for cat in unique_categories:
                        assigned_color = color_cycle[color_idx % len(color_cycle)]
                        color_idx += 1
                        sub_df = df[df[color_axis] == cat]
                        
                        # 🛠️ 入力されたカスタム凡例名を取得
                        custom_name = legend_names_config.get(f"{y_axis}_{cat}", f"{y_axis} ({cat})")
                        
                        # データ点のプロット（右側の凡例名にカスタム名が適用されます）
                        fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="markers", marker=dict(size=10, color=assigned_color), name=custom_name, yaxis=yaxis_id, legendgroup=f"{y_axis}_{cat}"))
                        
                        if selected_style == "全体の平均を通る一直線（トレンド線）":
                            x_t, y_t = get_trendline_data(sub_df, x_axis, y_axis)
                            if x_t is not None: 
                                fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=assigned_color, dash="solid"), name=f"{custom_name} (直線)", yaxis=yaxis_id, legendgroup=f"{y_axis}_{cat}", showlegend=False))
                        
                        elif selected_style == "数値を自動判定した線（曲線）":
                            shape_type = determine_shape(sub_df, x_axis, y_axis)
                            fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="lines", line=dict(shape=shape_type, color=assigned_color), name=f"{custom_name} (曲線)", yaxis=yaxis_id, legendgroup=f"{y_axis}_{cat}", showlegend=False))
                else:
                    assigned_color = color_cycle[color_idx % len(color_cycle)]
                    color_idx += 1
                    
                    # 🛠️ 入力されたカスタム凡例名を取得
                    custom_name = legend_names_config.get(y_axis, y_axis)
                    
                    # データ点のプロット（右側の凡例名にカスタム名が適用されます）
                    fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="markers", marker=dict(size=10, color=assigned_color), name=custom_name, yaxis=yaxis_id, legendgroup=y_axis))
                    
                    if selected_style == "全体の平均を通る一直線（トレンド線）":
                        x_t, y_t = get_trendline_data(df, x_axis, y_axis)
                        if x_t is not None: 
                            fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=assigned_color, dash="solid"), name=f"{custom_name} (直線)", yaxis=yaxis_id, legendgroup=y_axis, showlegend=False))
                    
                    elif selected_style == "数値を自動判定した線（曲線）":
                        shape_type = determine_shape(df, x_axis, y_axis)
                        fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="lines", line=dict(shape=shape_type, color=assigned_color), name=f"{custom_name} (曲線)", yaxis=yaxis_id, legendgroup=y_axis, showlegend=False))

            # 左軸の間隔を確保
            xaxis_start_domain = 0.0 + (max(0, len(axis_names) - 1) * 0.09)

            update_args = {
                "xaxis": dict(
                    title=dict(text=x_axis, font=dict(color="black")), 
                    range=x_range_input, 
                    domain=[xaxis_start_domain, 1.0],
                    tickfont=dict(color="black")
                ),
                "hovermode": "closest"
            }

            # 各軸のレイアウトを構築
            for i, name in enumerate(axis_names):
                actual_range = y_ranges_config.get(i) if custom_range else None
                
                axis_config = dict(
                    title=dict(text=name, font=dict(color="black"), standoff=20),
                    range=actual_range,
                    tickfont=dict(color="black"),
                    side="left"
                )
                
                if i > 0:
                    position_offset = xaxis_start_domain - (i * 0.09)
                    axis_config.update(dict(
                        overlaying="y",
                        anchor="free",
                        position=position_offset
                    ))
                
                axis_key = "yaxis" if i == 0 else f"yaxis{i + 1}"
                update_args[axis_key] = axis_config

            fig.update_layout(**update_args)

            # 最終描画
            st.plotly_chart(fig, use_container_width=True)

            # -----------------------------------------------------------------------------
            # 4. ファイル保存
            # -----------------------------------------------------------------------------
            st.header("4. データの保存")
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 入力データをCSVで保存", data=csv, file_name="graph_data.csv", mime="text/csv")
