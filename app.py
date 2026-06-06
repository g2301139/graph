import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from io import StringIO
import re

st.set_page_config(page_title="マルチデータ・万能グラフ作成アプリ", layout="wide")

st.title("📊 高機能マルチグラフ作成Webアプリ")
st.write("複数のデータを個別に入力・設定し、さらに選択したデータ同士を1つのグラフに合体できるようになりました。")

# -----------------------------------------------------------------------------
# セッション状態（State）の初期化
# -----------------------------------------------------------------------------
if "datasets" not in st.session_state:
    st.session_state.datasets = []

# -----------------------------------------------------------------------------
# 1. データの入力と管理
# -----------------------------------------------------------------------------
st.header("1. データの入力と管理")

default_paste_data = (
    "X軸データ\t売上\t利益\t目標値\tカテゴリー\n"
    "1000000\t10000000\t2\t8\tA\n"
    "2000000\t12000000\t5\t10\tB\n"
    "3000000\t18000000\t4\t15\tA\n"
    "4000000\t20000000\t8\t18\tB\n"
    "5000000\t26000000\t7\t22\tA"
)

with st.form("add_data_form", clear_on_submit=True):
    dataset_name = st.text_input("データの名前（例: 2026年第1Q、実験A など）", value=f"データセット {len(st.session_state.datasets) + 1}")
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
        
        st.session_state.datasets.append({
            "name": dataset_name,
            "df": new_df
        })
        st.success(f"「{dataset_name}」を追加しました！")
    except Exception as e:
        st.error(f"データの読み込みに失敗しました。エラー: {e}")

if st.session_state.datasets:
    st.subheader("現在登録されているデータ一覧")
    cols = st.columns(len(st.session_state.datasets) + 1)
    for idx, dataset in enumerate(st.session_state.datasets):
        with cols[idx]:
            st.info(f"📁 {dataset['name']} ({len(dataset['df'])}行)")
            if st.button(f"❌ 削除", key=f"del_{idx}"):
                st.session_state.datasets.pop(idx)
                st.rerun()

# 共通で使う補助関数
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

# -----------------------------------------------------------------------------
# 2. グラフの設定（データごと）
# -----------------------------------------------------------------------------
configs = {}

if st.session_state.datasets:
    st.header("2. グラフの設定（データごと）")
    st.write("上部のタブを切り替えて、データごとに描画したいX軸やY軸を設定してください。")
    
    tabs = st.tabs([d["name"] for d in st.session_state.datasets])
    
    for idx, dataset in enumerate(st.session_state.datasets):
        with tabs[idx]:
            df = dataset["df"]
            columns = df.columns.tolist()
            
            st.subheader(f"📊 「{dataset['name']}」の設定")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if len(columns) < 2:
                st.error("データの列が正しく分かれていません。")
                continue
                
            col1, col2, col3 = st.columns(3)
            with col1:
                x_axis = st.selectbox("X軸（横軸）を選択", options=columns, index=0, key=f"x_{idx}")
            with col2:
                default_y = [c for c in columns if c != x_axis and c != "カテゴリー"]
                if not default_y: default_y = [columns[0]]
                y_axes = st.multiselect("グラフに描画するデータ列を選択", options=columns, default=default_y, key=f"y_{idx}")
            with col3:
                color_axis = st.selectbox("色分けする列（オプション）", options=["なし"] + columns, index=0, key=f"color_{idx}")

            # 線の引き方・凡例名の個別設定
            line_styles_config = {}
            legend_names_config = {}
            if y_axes:
                st.markdown("##### 表示する線と凡例名（右側の名前）の設定")
                for y_col in y_axes:
                    style_col, name_col = st.columns(2)
                    with style_col:
                        line_style = st.selectbox(f"「{y_col}」の線の引き方", options=["マーカーのみ（線なし）", "数値を自動判定した線（曲線）", "全体の平均を通る一直線（トレンド線）"], index=1, key=f"style_{idx}_{y_col}")
                        line_styles_config[y_col] = line_style
                    with name_col:
                        if color_axis != "なし":
                            for cat in df[color_axis].unique():
                                def_name = f"[{dataset['name']}] {y_col} ({cat})"
                                custom_name = st.text_input(f"右側の表示名: {def_name}", value=def_name, key=f"legname_{idx}_{y_col}_{cat}")
                                legend_names_config[f"{y_col}_{cat}"] = custom_name
                        else:
                            def_name = f"[{dataset['name']}] {y_col}"
                            custom_name = st.text_input(f"右側の表示名: {def_name}", value=def_name, key=f"legname_{idx}_{y_col}")
                            legend_names_config[y_col] = custom_name

            configs[idx] = {
                "x_axis": x_axis,
                "y_axes": y_axes,
                "color_axis": color_axis,
                "line_styles": line_styles_config,
                "legend_names": legend_names_config
            }

            # 個別グラフの描画
            if y_axes:
                fig = go.Figure()
                color_cycle = px.colors.qualitative.Plotly
                c_idx = 0
                for y_axis in y_axes:
                    selected_style = line_styles_config.get(y_axis)
                    if color_axis != "なし":
                        for cat in df[color_axis].unique():
                            sub_df = df[df[color_axis] == cat]
                            c_name = legend_names_config.get(f"{y_axis}_{cat}")
                            color = color_cycle[c_idx % len(color_cycle)]
                            c_idx += 1
                            fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="markers", marker=dict(size=10, color=color), name=c_name, legendgroup=f"{idx}_{y_axis}_{cat}"))
                            if selected_style == "全体の平均を通る一直線（トレンド線）":
                                x_t, y_t = get_trendline_data(sub_df, x_axis, y_axis)
                                if x_t is not None: fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=color), name=f"{c_name} (直線)", legendgroup=f"{idx}_{y_axis}_{cat}", showlegend=False))
                            elif selected_style == "数値を自動判定した線（曲線）":
                                fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="lines", line=dict(shape=determine_shape(sub_df, x_axis, y_axis), color=color), name=f"{c_name} (曲線)", legendgroup=f"{idx}_{y_axis}_{cat}", showlegend=False))
                    else:
                        c_name = legend_names_config.get(y_axis)
                        color = color_cycle[c_idx % len(color_cycle)]
                        c_idx += 1
                        fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="markers", marker=dict(size=10, color=color), name=c_name, legendgroup=f"{idx}_{y_axis}"))
                        if selected_style == "全体の平均を通る一直線（トレンド線）":
                            x_t, y_t = get_trendline_data(df, x_axis, y_axis)
                            if x_t is not None: fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=color), name=f"{c_name} (直線)", legendgroup=f"{idx}_{y_axis}", showlegend=False))
                        elif selected_style == "数値を自動判定した線（曲線）":
                            fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="lines", line=dict(shape=determine_shape(df, x_axis, y_axis), color=color), name=f"{c_name} (曲線)", legendgroup=f"{idx}_{y_axis}", showlegend=False))
                
                fig.update_layout(
                    xaxis=dict(title=x_axis, tickformat="d"), 
                    yaxis=dict(title="値", tickformat="d"), 
                    hovermode="closest"
                )
                st.plotly_chart(fig, use_container_width=True, key=f"single_chart_{idx}")

    # -----------------------------------------------------------------------------
    # 3. グラフの合体セクション
    # -----------------------------------------------------------------------------
    st.markdown("---")
    st.header("3. 🔗 グラフの合体（重ね合わせ表示）")
    
    st.subheader("① 合体するデータセットの選択")
    selected_indices = []
    cb_cols = st.columns(len(st.session_state.datasets))
    for idx, dataset in enumerate(st.session_state.datasets):
        with cb_cols[idx]:
            if st.checkbox(f"合体する: {dataset['name']}", value=True, key=f"merge_cb_{idx}"):
                selected_indices.append(idx)

    if len(selected_indices) < 1:
        st.warning("合体するデータを1つ以上選択してください。")
    else:
        st.subheader("② 合体の基準と軸の設定")
        cc1, cc2 = st.columns(2)
        with cc1:
            match_mode = st.radio(
                "どの軸を共通（ベース）にして合体させますか？",
                options=[
                    "X軸（横軸）のみを合わせて、Y軸を追加していく", 
                    "Y軸（縦軸）のみを合わせて、X軸を追加していく",
                    "❌ どちらも合わせない（X軸・Y軸どちらも新しく追加していく）"
                ],
                index=0
            )
        with cc2:
            if match_mode != "❌ どちらも合わせない（X軸・Y軸どちらも新しく追加していく）":
                integrate_scales = st.checkbox("増える軸の目盛り（スケール）を1つに統合する", value=False)
            else:
                integrate_scales = False
                st.caption("※『どちらも合わせない』モードでは、すべての軸名と目盛が独立して作成されます。")

        merged_fig = go.Figure()
        color_cycle_merged = px.colors.qualitative.Alphabet
        merged_color_idx = 0
        update_layout_args = {"hovermode": "closest"}
        
        extra_x_count = 0  
        extra_y_count = 0  

        for loop_count, idx in enumerate(selected_indices):
            dataset = st.session_state.datasets[idx]
            df = dataset["df"]
            cfg = configs.get(idx)
            if not cfg or not cfg["y_axes"]: continue

            x_axis_name = cfg["x_axis"] 
            y_axis_name = ", ".join(cfg["y_axes"]) 
            
            x_axis = cfg["x_axis"]
            color_axis = cfg["color_axis"]
            line_styles = cfg["line_styles"]
            legend_names = cfg["legend_names"]

            # --- 改良された軸ロジック ---
            if match_mode == "X軸（横軸）のみを合わせて、Y軸を追加していく":
                xaxis_id = "x"
                if loop_count == 0:
                    update_layout_args["xaxis"] = dict(title=x_axis_name, tickformat="d", side="bottom")
                
                if loop_count == 0 or integrate_scales:
                    yaxis_id = "y"
                    if loop_count == 0:
                        update_layout_args["yaxis"] = dict(title=y_axis_name, tickformat="d", side="left")
                else:
                    extra_y_count += 1
                    yaxis_id = f"y{extra_y_count + 1}"
                    pos_offset = 0.0 - (extra_y_count * 0.08)
                    update_layout_args[f"yaxis{extra_y_count + 1}"] = dict(
                        title=dict(text=y_axis_name),
                        tickformat="d",
                        overlaying="y",
                        side="left", # 追加されるY軸を左側に並べる
                        anchor="free",
                        position=pos_offset
                    )
            
            elif match_mode == "Y軸（縦軸）のみを合わせて、X軸を追加していく":
                # 【修正】Y軸のみを合わせる（縦に重ねる）＝ Y軸という項目（名前）は同じ左側だが、
                # スケールが違う場合は「別の独立した目盛り」として右側に増やしていくことで潰れを防止
                xaxis_id = "x"
                if loop_count == 0:
                    update_layout_args["yaxis"] = dict(title=y_axis_name, tickformat="d", side="left")
                    update_layout_args["xaxis"] = dict(title=x_axis_name, tickformat="d", side="bottom")
                
                if loop_count == 0 or integrate_scales:
                    yaxis_id = "y"
                else:
                    extra_y_count += 1
                    yaxis_id = f"y{extra_y_count + 1}"
                    # 目盛りを統合しない場合は、2つ目以降のデータ専用Y軸を「右側」に配置して、値の潰れを防ぐ
                    pos_offset = 1.0 + (extra_y_count - 1) * 0.08
                    update_layout_args[f"yaxis{extra_y_count + 1}"] = dict(
                        title=dict(text=y_axis_name),
                        tickformat="d",
                        overlaying="y",
                        side="right", # 右側に個別の目盛りを生成
                        anchor="free",
                        position=pos_offset
                    )
                    
            else: # 「❌ どちらも合わせない」の場合
                if loop_count == 0:
                    xaxis_id = "x"
                    yaxis_id = "y"
                    update_layout_args["xaxis"] = dict(title=x_axis_name, tickformat="d", side="bottom")
                    update_layout_args["yaxis"] = dict(title=y_axis_name, tickformat="d", side="left")
                else:
                    extra_x_count += 1
                    extra_y_count += 1
                    xaxis_id = f"x{extra_x_count + 1}"
                    yaxis_id = f"y{extra_y_count + 1}"
                    
                    x_pos_offset = 0.0 - (extra_x_count * 0.08)
                    update_layout_args[f"xaxis{extra_x_count + 1}"] = dict(
                        title=dict(text=x_axis_name),
                        tickformat="d",
                        overlaying="x",
                        side="bottom",
                        anchor="free",
                        position=x_pos_offset
                    )
                    y_pos_offset = 0.0 - (extra_y_count * 0.08)
                    update_layout_args[f"yaxis{extra_y_count + 1}"] = dict(
                        title=dict(text=y_axis_name),
                        tickformat="d",
                        overlaying="y",
                        side="left", 
                        anchor="free",
                        position=y_pos_offset
                    )

            # データのプロット
            for y_axis in cfg["y_axes"]:
                selected_style = line_styles.get(y_axis)
                trace_xaxis = "x" if xaxis_id == "x" else xaxis_id
                trace_yaxis = "y" if yaxis_id == "y" else yaxis_id
                
                if color_axis != "なし":
                    for cat in df[color_axis].unique():
                        sub_df = df[df[color_axis] == cat]
                        c_name = legend_names.get(f"{y_axis}_{cat}")
                        color = color_cycle_merged[merged_color_idx % len(color_cycle_merged)]
                        merged_color_idx += 1

                        merged_fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="markers", marker=dict(size=10, color=color), name=c_name, xaxis=trace_xaxis, yaxis=trace_yaxis, legendgroup=f"m_{idx}_{y_axis}_{cat}"))
                        if selected_style == "全体の平均を通る一直線（トレンド線）":
                            x_t, y_t = get_trendline_data(sub_df, x_axis, y_axis)
                            if x_t is not None: merged_fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=color), xaxis=trace_xaxis, yaxis=trace_yaxis, legendgroup=f"m_{idx}_{y_axis}_{cat}", showlegend=False))
                        elif selected_style == "数値を自動判定した線（曲線）":
                            merged_fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="lines", line=dict(shape=determine_shape(sub_df, x_axis, y_axis), color=color), xaxis=trace_xaxis, yaxis=trace_yaxis, legendgroup=f"m_{idx}_{y_axis}_{cat}", showlegend=False))
                else:
                    c_name = legend_names.get(y_axis)
                    color = color_cycle_merged[merged_color_idx % len(color_cycle_merged)]
                    merged_color_idx += 1

                    merged_fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="markers", marker=dict(size=10, color=color), name=c_name, xaxis=trace_xaxis, yaxis=trace_yaxis, legendgroup=f"m_{idx}_{y_axis}"))
                    if selected_style == "全体の平均を通る一直線（トレンド線）":
                        x_t, y_t = get_trendline_data(df, x_axis, y_axis)
                        if x_t is not None: merged_fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=color), xaxis=trace_xaxis, yaxis=trace_yaxis, legendgroup=f"m_{idx}_{y_axis}", showlegend=False))
                    elif selected_style == "数値を自動判定した線（曲線）":
                        merged_fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="lines", line=dict(shape=determine_shape(df, x_axis, y_axis), color=color), xaxis=trace_xaxis, yaxis=trace_yaxis, legendgroup=f"m_{idx}_{y_axis}", showlegend=False))

        if integrate_scales:
            if match_mode in ["X軸（横軸）のみを合わせて、Y軸を追加していく", "Y軸（縦軸）のみを合わせて、X軸を追加していく"]:
                update_layout_args["yaxis"] = dict(title="共通縦軸 (Y)", tickformat="d", side="left")

        # 動的マージン調整（左と右の両方の増加に対応）
        # 「X軸のみ合わせる」「どちらも合わせない」は左が増える
        # 「Y軸のみ合わせる」は右が増える
        left_margin = 80 + (extra_y_count * 75) if match_mode != "Y軸（縦軸）のみを合わせて、X軸を追加していく" else 80
        right_margin = 80 + (extra_y_count * 75) if match_mode == "Y軸（縦軸）のみを合わせて、X軸を追加していく" else 50
        update_layout_args["margin"] = dict(l=left_margin, r=right_margin)

        # レイアウト適用
        merged_fig.update_layout(**update_layout_args)
        
        # 高さの自動拡張
        fig_height = 500 + (extra_x_count * 45)

        st.subheader("📉 合体したグラフ")
        st.plotly_chart(merged_fig, use_container_width=True, height=fig_height, key="merged_chart_view")
else:
    st.info("データがまだ登録されていません。まずは上のフォームからデータを追加してください。")
