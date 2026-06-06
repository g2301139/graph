import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from io import StringIO
import re

st.set_page_config(page_title="万能グラフ作成アプリ", layout="wide")

st.title("📊 高機能グラフ作成Webアプリ")
st.write("凡例名（右側の名前）の入力ボックスを完全に独立化させました。1つ1つの名前を個別に変更可能です。")

# -----------------------------------------------------------------------------
# 1. データ入力セクション
# -----------------------------------------------------------------------------
st.header("1. データの入力")

default_paste_data = (
    "X軸データ1\tX軸データ2\t売上\t利益\tカテゴリー\n"
    "100000\t10\t1000000\t2\tA\n"
    "200000\t20\t1200000\t5\tB\n"
    "300000\t15\t1800000\t4\tA\n"
    "400000\t30\t2000000\t8\tB\n"
    "500000\t25\t2600000\t7\tA"
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
            x_axes = st.multiselect("X軸（横軸）を選択（複数選択可）", options=columns, default=[columns[0]])
        with col2:
            default_y = [c for c in columns if c not in x_axes and c != "カテゴリー"]
            if not default_y:
                default_y = [columns[0]]
            y_axes = st.multiselect("グラフに描画するデータ列を選択（複数選択可）", options=columns, default=default_y)
        with col3:
            color_axis = st.selectbox("色分けする列（オプション）", options=["なし"] + columns, index=0)

        # X軸（横軸）の配置・統合設定
        st.subheader("X軸（横軸）の配置設定")
        x_axis_names = []
        data_x_axis_mapping = {}
        is_x_integrated = False

        if x_axes:
            if len(x_axes) > 1:
                is_x_integrated = st.checkbox("選択したデータのX軸（名前）を1つに統合する", value=False, key="x_integrate_cb")
                if is_x_integrated:
                    integrated_x_name = st.text_input("統合後のX軸の名前を入力してください", value="統合されたX軸")
                    x_axis_names = [integrated_x_name]
                    for x_col in x_axes:
                        data_x_axis_mapping[x_col] = {"axis_idx": 0, "axis_name": integrated_x_name}
                else:
                    x_axis_names = list(x_axes)
                    for idx, x_col in enumerate(x_axes):
                        data_x_axis_mapping[x_col] = {"axis_idx": idx, "axis_name": x_col}
            else:
                x_axis_names = list(x_axes)
                data_x_axis_mapping[x_axes[0]] = {"axis_idx": 0, "axis_name": x_axes[0]}
        else:
            x_axis_names = ["X軸"]

        # 縦軸（Y軸）の配置・統合設定
        st.subheader("縦軸（Y軸）の配置設定")
        axis_names = []
        data_axis_mapping = {}
        is_integrated = False

        if y_axes:
            if len(y_axes) > 1:
                is_integrated = st.checkbox("選択したデータの縦軸（名前）を1つに統合する", value=False, key="y_integrate_cb")
                
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

        # 🛠️【完全独立化】表示する線と凡例名（右側の名前）の設定
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
                        # 色分けのカテゴリー一覧を取得
                        unique_categories = df[color_axis].unique()
                        for cat in unique_categories:
                            # 1つ1つ絶対に重複しないシステムキー（uniq_key）を作成して入力欄を完全分離
                            uniq_key = f"input_legend_{y_col}_{color_axis}_{cat}"
                            default_legend_name = f"{y_col} ({cat})"
                            
                            custom_legend_name = st.text_input(
                                f"右側に表示する名前: {default_legend_name}", 
                                value=default_legend_name, 
                                key=uniq_key
                            )
                            # 保存用辞書には「データ名_カテゴリ名」をキーにして格納
                            legend_names_config[f"{y_col}_{cat}"] = custom_legend_name
                    else:
                        uniq_key = f"input_legend_{y_col}_none"
                        default_legend_name = y_col
                        custom_legend_name = st.text_input(
                            f"右側に表示する名前: {default_legend_name}", 
                            value=default_legend_name, 
                            key=uniq_key
                        )
                        legend_names_config[y_col] = custom_legend_name

        # 手動範囲設定
        st.subheader("軸の表示範囲設定")
        custom_range = st.checkbox("手動で軸の最大値・最小値を指定する")
        
        x_ranges_config = {}
        y_ranges_config = {}

        if custom_range:
            st.write("▼ X軸の範囲設定")
            for i, name in enumerate(x_axis_names):
                st.markdown(f"**{name}** の範囲")
                cx1, cx2 = st.columns(2)
                try:
                    if is_x_integrated:
                        x_min_def = float(df[x_axes].min().min())
                        x_max_def = float(df[x_axes].max().max())
                    else:
                        x_min_def = float(df[name].min())
                        x_max_def = float(df[name].max())
                except:
                    x_min_def, x_max_def = 0.0, 100.0
                with cx1: x_min = st.number_input(f"最小値 ({name})", value=x_min_def, key=f"xmin_{i}")
                with cx2: x_max = st.number_input(f"最大値 ({name})", value=x_max_def, key=f"xmax_{i}")
                x_ranges_config[i] = [x_min, x_max]
            
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

        if not x_axes or not y_axes:
            st.warning("X軸とデータ列（Y軸）をそれぞれ1つ以上選択してください。")
        else:
            left_margin_domain = 0.0 + (max(0, len(axis_names) - 1) * 0.08)
            
            # すべてのX軸が下に並ぶため、下側（b）のマージンを自動計算
            extra_bottom_margin = 80 + (len(x_axis_names) * 50)
            init_layout_args = {
                "hovermode": "closest",
                "margin": dict(t=50, b=extra_bottom_margin, l=60, r=50)
            }

            # 全X軸・下部並列化
            for i, name in enumerate(x_axis_names):
                actual_x_range = x_ranges_config.get(i) if custom_range else None
                x_key = "xaxis" if i == 0 else f"xaxis{i + 1}"
                
                x_dict = {
                    "range": actual_x_range,
                    "tickfont": dict(color="black"),
                    "tickformat": ".0f",
                    "domain": [left_margin_domain, 1.0],
                    "showgrid": True if i == 0 else False,
                    "side": "bottom"
                }
                
                if i == 0:
                    x_dict["title"] = dict(text=name, font=dict(color="black"), standoff=15)
                else:
                    x_dict["overlaying"] = "x"
                    break_lines = "<br>" * i
                    x_dict["title"] = dict(text=f"{break_lines}{name}", font=dict(color="black"))
                
                init_layout_args[x_key] = go.layout.XAxis(**x_dict)

            # Y軸の定義
            for i, name in enumerate(axis_names):
                actual_range = y_ranges_config.get(i) if custom_range else None
                axis_key = "yaxis" if i == 0 else f"yaxis{i + 1}"
                
                y_dict = {
                    "title": dict(text=name, font=dict(color="black"), standoff=15),
                    "range": actual_range,
                    "tickfont": dict(color="black"),
                    "tickformat": ".0f",
                    "side": "left",
                    "showgrid": True if i == 0 else False
                }
                if i > 0:
                    position_offset = left_margin_domain - (i * 0.08)
                    y_dict.update({
                        "overlaying": "y",
                        "anchor": "free",
                        "position": max(0.0, position_offset)
                    })
                init_layout_args[axis_key] = go.layout.YAxis(**y_dict)

            fig = go.Figure(layout=go.Layout(**init_layout_args))

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

            # 描画ループ
            for y_idx, y_axis in enumerate(y_axes):
                x_axis = x_axes[min(y_idx, len(x_axes) - 1)]
                
                x_mapping = data_x_axis_mapping.get(x_axis)
                if not x_mapping: continue
                x_ax_idx = x_mapping["axis_idx"]
                xaxis_id = "x" if x_ax_idx == 0 else f"x{x_ax_idx + 1}"
                
                y_mapping = data_axis_mapping.get(y_axis)
                if not y_mapping: continue
                y_ax_idx = y_mapping["axis_idx"]
                yaxis_id = "y" if y_ax_idx == 0 else f"y{y_ax_idx + 1}"
                
                selected_style = line_styles_config.get(y_axis, "数値を自動判定した線（曲線）")

                if color_axis != "なし":
                    unique_categories = df[color_axis].unique()
                    for cat in unique_categories:
                        assigned_color = color_cycle[color_idx % len(color_cycle)]
                        color_idx += 1
                        sub_df = df[df[color_axis] == cat]
                        
                        # 保存された独立な名前設定を正しく適用
                        custom_name = legend_names_config.get(f"{y_axis}_{cat}", f"{y_axis} ({cat})")
                        
                        fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="markers", marker=dict(size=10, color=assigned_color), name=custom_name, xaxis=xaxis_id, yaxis=yaxis_id, legendgroup=f"{y_axis}_{cat}"))
                        
                        if selected_style == "全体の平均を通る一直線（トレンド線）":
                            x_t, y_t = get_trendline_data(sub_df, x_axis, y_axis)
                            if x_t is not None: 
                                fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=assigned_color, dash="solid"), name=f"{custom_name} (直線)", xaxis=xaxis_id, yaxis=yaxis_id, legendgroup=f"{y_axis}_{cat}", showlegend=False))
                        elif selected_style == "数値を自動判定した線（曲線）":
                            shape_type = determine_shape(sub_df, x_axis, y_axis)
                            fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="lines", line=dict(shape=shape_type, color=assigned_color), name=f"{custom_name} (曲線)", xaxis=xaxis_id, yaxis=yaxis_id, legendgroup=f"{y_axis}_{cat}", showlegend=False))
                else:
                    assigned_color = color_cycle[color_idx % len(color_cycle)]
                    color_idx += 1
                    custom_name = legend_names_config.get(y_axis, y_axis)
                    
                    fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="markers", marker=dict(size=10, color=assigned_color), name=custom_name, xaxis=xaxis_id, yaxis=yaxis_id, legendgroup=y_axis))
                    
                    if selected_style == "全体の平均を通る一直線（トレンド線）":
                        x_t, y_t = get_trendline_data(df, x_axis, y_axis)
                        if x_t is not None: 
                            fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=assigned_color, dash="solid"), name=f"{custom_name} (直線)", xaxis=xaxis_id, yaxis=yaxis_id, legendgroup=y_axis, showlegend=False))
                    elif selected_style == "数値を自動判定した線（曲線）":
                        shape_type = determine_shape(df, x_axis, y_axis)
                        fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="lines", line=dict(shape=shape_type, color=assigned_color), name=f"{custom_name} (曲線)", xaxis=xaxis_id, yaxis=yaxis_id, legendgroup=y_axis, showlegend=False))

            st.plotly_chart(fig, use_container_width=True)

            # -----------------------------------------------------------------------------
            # 4. ファイル保存
            # -----------------------------------------------------------------------------
            st.header("4. データの保存")
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 入力データをCSVで保存", data=csv, file_name="graph_data.csv", mime="text/csv")
