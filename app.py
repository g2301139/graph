import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from io import StringIO
import re

st.set_page_config(page_title="マルチデータ・万能グラフ作成アプリ", layout="wide")

st.title("📊 高機能マルチグラフ作成Webアプリ")
st.write("複数のデータを個別に入力し、それぞれのグラフをカスタマイズして作成・管理できるようになりました。")

# -----------------------------------------------------------------------------
# セッション状態（State）の初期化
# -----------------------------------------------------------------------------
# 複数のデータセットを保持するリスト。各要素は dict
if "datasets" not in st.session_state:
    st.session_state.datasets = []

# -----------------------------------------------------------------------------
# 1. データの追加・管理セクション
# -----------------------------------------------------------------------------
st.header("1. データの入力と管理")

default_paste_data = (
    "X軸データ\t売上\t利益\t目標値\tカテゴリー\n"
    "1\t10\t2\t8\tA\n"
    "2\t12\t5\t10\tB\n"
    "3\t18\t4\t15\tA\n"
    "4\t20\t8\t18\tB\n"
    "5\t26\t7\t22\tA"
)

# フォームを使って新しいデータを追加
with st.form("add_data_form", clear_on_submit=True):
    dataset_name = st.text_input("データの名前（例: 2026年第1四半期、実験A など）", value=f"データセット {len(st.session_state.datasets) + 1}")
    paste_input = st.text_area(
        "Excelやスプレッドシートからデータをコピーし、下の枠内に貼り付けてください（Ctrl+V）：",
        value=default_paste_data,
        height=150
    )
    submit_button = st.form_submit_button("📥 このデータをアプリに追加する")

if submit_button and paste_input.strip():
    try:
        lines = paste_input.strip().split('\n')
        processed_lines = []
        for line in lines:
            if ',' not in line:
                line = re.sub(r'[\t\s ]+', '\t', line)
            processed_lines.append(line)
        
        final_input = '\n'.join(processed_lines)
        sep_char = ',' if ',' in processed_lines[0] else '\t'
        
        new_df = pd.read_csv(StringIO(final_input), sep=sep_char)
        if len(new_df.columns) == 1:
            new_df = pd.read_csv(StringIO(final_input), sep=r'\s+', engine='python')
        
        # セッション状態に保存
        st.session_state.datasets.append({
            "name": dataset_name,
            "df": new_df
        })
        st.success(f"「{dataset_name}」を追加しました！")
    except Exception as e:
        st.error(f"データの読み込みに失敗しました。エラー: {e}")

# 登録済みデータのリスト表示と削除機能
if st.session_state.datasets:
    st.subheader("現在登録されているデータ一覧")
    cols = st.columns(len(st.session_state.datasets) + 1)
    for idx, dataset in enumerate(st.session_state.datasets):
        with cols[idx]:
            st.info(f"📁 {dataset['name']} ({len(dataset['df'])}行)")
            if st.button(f"❌ 削除", key=f"del_{idx}"):
                st.session_state.datasets.pop(idx)
                st.rerun()

---

# -----------------------------------------------------------------------------
# 2. グラフの設定 & 描画セクション（個別管理）
# -----------------------------------------------------------------------------
if st.session_state.datasets:
    st.header("2. グラフの設定と生成")
    st.write("上部のタブを切り替えて、データごとに個別のグラフを設定できます。")
    
    # 登録されたデータセットごとにタブを作成して処理を分離
    tabs = st.tabs([d["name"] for d in st.session_state.datasets])
    
    for idx, dataset in enumerate(st.session_state.datasets):
        with tabs[idx]:
            df = dataset["df"]
            columns = df.columns.tolist()
            
            st.subheader(f"📊 「{dataset['name']}」のデータ確認と設定")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if len(columns) < 2:
                st.error("データの列が正しく分かれていません。貼り付けるデータの区切りを確認してください。")
                continue
                
            # 各ウィジェットのkeyに `idx`（インデックス）を付与して衝突を防ぐ
            col1, col2, col3 = st.columns(3)
            with col1:
                x_axis = st.selectbox("X軸（横軸）を選択", options=columns, index=0, key=f"x_{idx}")
            with col2:
                default_y = [c for c in columns if c != x_axis and c != "カテゴリー"]
                if not default_y:
                    default_y = [columns[0]]
                y_axes = st.multiselect("グラフに描画するデータ列を選択（複数選択可）", options=columns, default=default_y, key=f"y_{idx}")
            with col3:
                color_axis = st.selectbox("色分けする列（オプション）", options=["なし"] + columns, index=0, key=f"color_{idx}")

            # 縦軸（Y軸）の配置・統合設定
            st.markdown("#### 縦軸（Y軸）の配置設定")
            axis_names = []
            data_axis_mapping = {}
            is_integrated = False

            if y_axes:
                if len(y_axes) > 1:
                    is_integrated = st.checkbox("選択したデータの縦軸（名前）を1つに統合する", value=False, key=f"integ_{idx}")
                    if is_integrated:
                        integrated_name = st.text_input("統合後の縦軸の名前を入力してください", value="統合された縦軸", key=f"integ_name_{idx}")
                        axis_names = [integrated_name]
                        for y_col in y_axes:
                            data_axis_mapping[y_col] = {"axis_idx": 0, "axis_name": integrated_name}
                    else:
                        axis_names = list(y_axes)
                        for y_idx, y_col in enumerate(y_axes):
                            data_axis_mapping[y_col] = {"axis_idx": y_idx, "axis_name": y_col}
                else:
                    axis_names = list(y_axes)
                    data_axis_mapping[y_axes[0]] = {"axis_idx": 0, "axis_name": y_axes[0]}
            else:
                axis_names = ["縦軸"]

            # 線と凡例名の設定
            st.markdown("#### 表示する線と凡例名（右側の名前）の設定")
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
                            key=f"style_{idx}_{y_col}"
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
                                    key=f"legname_{idx}_{y_col}_{cat}"
                                )
                                legend_names_config[f"{y_col}_{cat}"] = custom_legend_name
                        else:
                            default_legend_name = y_col
                            custom_legend_name = st.text_input(
                                f"右側に表示する名前: {default_legend_name}", 
                                value=default_legend_name, 
                                key=f"legname_{idx}_{y_col}"
                            )
                            legend_names_config[y_col] = custom_legend_name

            # 軸の表示範囲設定
            st.markdown("#### 軸の表示範囲設定")
            custom_range = st.checkbox("手動で軸の最大値・最小値を指定する", key=f"custom_range_{idx}")
            
            try:
                x_min_def, x_max_def = float(df[x_axis].min()), float(df[x_axis].max())
            except:
                x_min_def, x_max_def = 0.0, 100.0

            x_range_input = None
            y_ranges_config = {}

            if custom_range:
                cx1, cx2 = st.columns(2)
                with cx1: x_min = st.number_input("X軸 最小値", value=x_min_def, key=f"xmin_{idx}")
                with cx2: x_max = st.number_input("X軸 最大値", value=x_max_def, key=f"xmax_{idx}")
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
                    
                    with cy1: y_min = st.number_input(f"最小値 ({name})", value=y_min_def, key=f"ymin_{idx}_{i}")
                    with cy2: y_max = st.number_input(f"最大値 ({name})", value=y_max_def, key=f"ymax_{idx}_{i}")
                    y_ranges_config[i] = [y_min, y_max]

            # -----------------------------------------------------------------
            # グラフ描画ロジック
            # -----------------------------------------------------------------
            st.markdown("### 📉 生成されたグラフ")
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
                        ridx = np.isfinite(x_vals) & np.isfinite(y_vals)
                        a, b = np.polyfit(x_vals[ridx], y_vals[ridx], 1)
                        return np.array([min(x_vals), max(x_vals)]), a * np.array([min(x_vals), max(x_vals)]) + b
                    except: return None, None

                def determine_shape(dataframe, x, y):
                    try:
                        x_val, y_val = pd.to_numeric(dataframe[x]).values, pd.to_numeric(dataframe[y]).values
                        if len(x_val) < 3: return "linear"
                        return "linear" if np.var(np.diff(np.diff(y_val) / np.diff(x_val))) < 1e-5 else "spline"
                    except: return "linear"

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
                            custom_name = legend_names_config.get(f"{y_axis}_{cat}", f"{y_axis} ({cat})")
                            
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
                        custom_name = legend_names_config.get(y_axis, y_axis)
                        
                        fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="markers", marker=dict(size=10, color=assigned_color), name=custom_name, yaxis=yaxis_id, legendgroup=y_axis))
                        
                        if selected_style == "全体の平均を通る一直線（トレンド線）":
                            x_t, y_t = get_trendline_data(df, x_axis, y_axis)
                            if x_t is not None: 
                                fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=assigned_color, dash="solid"), name=f"{custom_name} (直線)", yaxis=yaxis_id, legendgroup=y_axis, showlegend=False))
                        elif selected_style == "数値を自動判定した線（曲線）":
                            shape_type = determine_shape(df, x_axis, y_axis)
                            fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="lines", line=dict(shape=shape_type, color=assigned_color), name=f"{custom_name} (曲線)", yaxis=yaxis_id, legendgroup=y_axis, showlegend=False))

                xaxis_start_domain = 0.0 + (max(0, len(axis_names) - 1) * 0.09)
                update_args = {
                    "xaxis": dict(title=dict(text=x_axis, font=dict(color="black")), range=x_range_input, domain=[xaxis_start_domain, 1.0], tickfont=dict(color="black")),
                    "hovermode": "closest"
                }

                for i, name in enumerate(axis_names):
                    actual_range = y_ranges_config.get(i) if custom_range else None
                    axis_config = dict(title=dict(text=name, font=dict(color="black"), standoff=20), range=actual_range, tickfont=dict(color="black"), side="left")
                    if i > 0:
                        position_offset = xaxis_start_domain - (i * 0.09)
                        axis_config.update(dict(overlaying="y", anchor="free", position=position_offset))
                    
                    axis_key = "yaxis" if i == 0 else f"yaxis{i + 1}"
                    update_args[axis_key] = axis_config

                fig.update_layout(**update_args)
                st.plotly_chart(fig, use_container_width=True, key=f"chart_{idx}")

                # 個別データの保存
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(label=f"📥 「{dataset['name']}」のデータをCSVで保存", data=csv, file_name=f"{dataset['name']}.csv", mime="text/csv", key=f"dl_{idx}")
else:
    st.info("データがまだ登録されていません。まずは「1. データの入力と管理」からデータを追加してください。")
