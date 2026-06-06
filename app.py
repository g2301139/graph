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
    dataset_name = st.text_input("データの名前（例: 2026年第1Q、実験A、シェルソート など）", value=f"データセット {len(st.session_state.datasets) + 1}")
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
                x_axis = st.selectbox("X軸（横軸）データ列を選択", options=columns, index=0, key=f"x_{idx}")
            with col2:
                default_y = [c for c in columns[1:] if c != "カテゴリー"]
                if not default_y: default_y = [columns[0]]
                y_axes = st.multiselect("グラフに描画するY軸データ列を選択", options=columns, default=default_y, key=f"y_{idx}")
            with col3:
                color_axis = st.selectbox("色分けする列（オプション）", options=["なし"] + columns, index=0, key=f"color_{idx}")

            st.markdown("✏️ **軸の名前（ラベル）を編集**")
            label_col1, label_col2 = st.columns(2)
            with label_col1:
                custom_x_label = st.text_input("横軸（X軸）の表示名", value=x_axis, key=f"label_x_{idx}_{dataset['name']}")
            with label_col2:
                default_y_label = ", ".join(y_axes) if y_axes else "値"
                custom_y_label = st.text_input("縦軸（Y軸）の表示名", value=default_y_label, key=f"label_y_{idx}_{dataset['name']}")

            # 線の引き方・凡例名の個別設定
            line_styles_config = {}
            legend_names_config = {}
            if y_axes:
                st.markdown("##### 表示スタイルと右側の表示名（凡例）の設定")
                for y_col in y_axes:
                    style_col, name_col = st.columns(2)
                    with style_col:
                        line_style = st.selectbox(
                            f"「{y_col}」の表示スタイル", 
                            options=["点（マーカー）のみ", "線のみ（曲線）", "点と線（両方）", "トレンド線（直線）"], 
                            index=2, 
                            key=f"style_{idx}_{y_col}"
                        )
                        line_styles_config[y_col] = line_style
                    with name_col:
                        if color_axis != "なし":
                            for cat in df[color_axis].unique():
                                def_name = f"{dataset['name']} ({cat})"
                                custom_name = st.text_input(f"右側の表示名: {y_col}", value=def_name, key=f"legname_{idx}_{dataset['name']}_{y_col}_{cat}")
                                legend_names_config[f"{y_col}_{cat}"] = custom_name
                        else:
                            def_name = f"{dataset['name']}"
                            custom_name = st.text_input(f"右側の表示名: {y_col}", value=def_name, key=f"legname_{idx}_{dataset['name']}_{y_col}")
                            legend_names_config[y_col] = custom_name

            configs[idx] = {
                "x_axis": x_axis,
                "y_axes": y_axes,
                "color_axis": color_axis,
                "line_styles": line_styles_config,
                "legend_names": legend_names_config,
                "custom_x_label": custom_x_label,
                "custom_y_label": custom_y_label
            }

            # 個別グラフの描画
            if y_axes:
                fig = go.Figure()
                color_cycle = px.colors.qualitative.Plotly
                c_idx = 0
                for y_axis in y_axes:
                    selected_style = line_styles_config.get(y_axis)
                    
                    if selected_style == "点（マーカー）のみ":
                        plot_mode = "markers"
                    elif selected_style == "線のみ（曲線）":
                        plot_mode = "lines"
                    else:
                        plot_mode = "markers+lines"
                        
                    if color_axis != "なし":
                        for cat in df[color_axis].unique():
                            sub_df = df[df[color_axis] == cat]
                            c_name = legend_names_config.get(f"{y_axis}_{cat}")
                            color = color_cycle[c_idx % len(color_cycle)]
                            c_idx += 1
                            
                            if selected_style == "トレンド線（直線）":
                                fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="markers", marker=dict(size=10, color=color), name=c_name))
                                x_t, y_t = get_trendline_data(sub_df, x_axis, y_axis)
                                if x_t is not None: fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=color), name=f"{c_name} (トレンド線)"))
                            else:
                                fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode=plot_mode, line=dict(shape=determine_shape(sub_df, x_axis, y_axis), color=color), marker=dict(size=10), name=c_name))
                    else:
                        c_name = legend_names_config.get(y_axis)
                        color = color_cycle[c_idx % len(color_cycle)]
                        c_idx += 1
                        
                        if selected_style == "トレンド線（直線）":
                            fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="markers", marker=dict(size=10, color=color), name=c_name))
                            x_t, y_t = get_trendline_data(df, x_axis, y_axis)
                            if x_t is not None: fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=color), name=f"{c_name} (トレンド線)"))
                        else:
                            fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode=plot_mode, line=dict(shape=determine_shape(df, x_axis, y_axis), color=color), marker=dict(size=10), name=c_name))
                
                fig.update_layout(
                    title=dict(text=f"📊 グラフ: {dataset['name']}", font=dict(size=18)),
                    xaxis=dict(title=custom_x_label, tickformat="d"), 
                    yaxis=dict(title=custom_y_label, tickformat="d"), 
                    hovermode="closest"
                )
                st.plotly_chart(fig, use_container_width=True, key=f"single_chart_{idx}")

    # -----------------------------------------------------------------------------
    # 3. グラフの合体セクション（X軸共通化・マルチY軸モード）
    # -----------------------------------------------------------------------------
    st.markdown("---")
    st.header("3. 🔗 グラフの合体（重ね合わせ表示）")
    st.write("各データセットのX軸を基準にして、1つのグラフに統合します。")
    
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
        st.subheader("② 目盛り（スケール）と軸名（ラベル）の設定")
        
        # ご指定通り文言を「y軸を固定して合体する」に変更しました
        integrate_scales = st.checkbox("ｙ軸を固定して合体する", value=False)

        st.markdown("✏️ **合体グラフの軸ラベル名編集**")
        
        first_cfg = configs.get(selected_indices[0]) if selected_indices else None
        default_merged_x_label = first_cfg["custom_x_label"] if first_cfg else "共通横軸 (X)"
        
        merged_x_title = st.text_input("合体グラフの横軸（X軸）名", value=default_merged_x_label, key="merged_label_x")

        custom_axis_titles = {}
        axis_label_idx = 0
        for loop_count, idx in enumerate(selected_indices):
            dataset = st.session_state.datasets[idx]
            cfg = configs.get(idx)
            if not cfg or not cfg["y_axes"]: continue
            
            default_title = cfg["custom_y_label"]
            
            if loop_count == 0:
                # y軸固定時は「共通縦軸」、マルチ軸時はそれぞれのデータ名に
                label_text = "共通の縦軸名（Y軸）" if integrate_scales else f"ベースとなる左側の縦軸名（第1 Y軸: {dataset['name']} 用）"
                custom_axis_titles["y"] = st.text_input(label_text, value="共通縦軸 (Y)" if integrate_scales else default_title, key=f"custom_title_y_{dataset['name']}")
            elif not integrate_scales:
                axis_label_idx += 1
                label_text = f"右側に追加される縦軸名（第{axis_label_idx + 1} Y軸: {dataset['name']} 用）"
                custom_axis_titles[f"y_axis_{idx}"] = st.text_input(label_text, value=default_title, key=f"custom_title_y_{idx}_{dataset['name']}")

        merged_fig = go.Figure()
        color_cycle_merged = px.colors.qualitative.Alphabet
        merged_color_idx = 0
        update_layout_args = {"hovermode": "closest"}
        
        extra_y_count = 0  

        for loop_count, idx in enumerate(selected_indices):
            dataset = st.session_state.datasets[idx]
            df = dataset["df"]
            cfg = configs.get(idx)
            if not cfg or not cfg["y_axes"]: continue

            x_axis = cfg["x_axis"]
            color_axis = cfg["color_axis"]
            line_styles = cfg["line_styles"]
            legend_names = cfg["legend_names"]

            # --- 軸の配置ロジック ---
            xaxis_id = "x"
            if loop_count == 0:
                update_layout_args["xaxis"] = dict(title=merged_x_title, tickformat="d", side="bottom")
            
            if loop_count == 0 or integrate_scales:
                yaxis_id = "y"
                if loop_count == 0:
                    update_layout_args["yaxis"] = dict(title=custom_axis_titles.get("y", "縦軸"), tickformat="d", side="left")
            else:
                extra_y_count += 1
                yaxis_id = f"y{extra_y_count + 1}"
                
                pos_offset = 1.0 + ((extra_y_count - 1) * 0.08)
                update_layout_args[f"yaxis{extra_y_count + 1}"] = dict(
                    title=dict(text=custom_axis_titles.get(f"y_axis_{idx}", f"縦軸 {extra_y_count + 1}")),
                    tickformat="d",
                    overlaying="y",
                    side="right", 
                    anchor="free",
                    position=pos_offset
                )

            # データのプロット
            for y_axis in cfg["y_axes"]:
                selected_style = line_styles.get(y_axis)
                trace_xaxis = "x" if xaxis_id == "x" else xaxis_id
                trace_yaxis = "y" if yaxis_id == "y" else yaxis_id
                
                if selected_style == "点（マーカー）のみ":
                    plot_mode = "markers"
                elif selected_style == "線のみ（曲線）":
                    plot_mode = "lines"
                else:
                    plot_mode = "markers+lines"
                
                if color_axis != "なし":
                    for cat in df[color_axis].unique():
                        sub_df = df[df[color_axis] == cat]
                        c_name = legend_names.get(f"{y_axis}_{cat}")
                        color = color_cycle_merged[merged_color_idx % len(color_cycle_merged)]
                        merged_color_idx += 1

                        if selected_style == "トレンド線（直線）":
                            merged_fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="markers", marker=dict(size=10, color=color), name=c_name, xaxis=trace_xaxis, yaxis=trace_yaxis))
                            x_t, y_t = get_trendline_data(sub_df, x_axis, y_axis)
                            if x_t is not None: merged_fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=color), name=f"{c_name} (トレンド線)", xaxis=trace_xaxis, yaxis=trace_yaxis))
                        else:
                            merged_fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode=plot_mode, line=dict(shape=determine_shape(sub_df, x_axis, y_axis), color=color), marker=dict(size=10), name=c_name, xaxis=trace_xaxis, yaxis=trace_yaxis))
                else:
                    c_name = legend_names.get(y_axis)
                    color = color_cycle_merged[merged_color_idx % len(color_cycle_merged)]
                    merged_color_idx += 1

                    if selected_style == "トレンド線（直線）":
                        merged_fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="markers", marker=dict(size=10, color=color), name=c_name, xaxis=trace_xaxis, yaxis=trace_yaxis))
                        x_t, y_t = get_trendline_data(df, x_axis, y_axis)
                        if x_t is not None: merged_fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=color), name=f"{c_name} (トレンド線)", xaxis=trace_xaxis, yaxis=trace_yaxis))
                    else:
                        merged_fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode=plot_mode, line=dict(shape=determine_shape(df, x_axis, y_axis), color=color), marker=dict(size=10), name=c_name, xaxis=trace_xaxis, yaxis=trace_yaxis))

        right_margin = 50 + (max(0, extra_y_count) * 75)
        update_layout_args["margin"] = dict(l=80, r=right_margin)

        # レイアウト適用
        merged_fig.update_layout(**update_layout_args)

        st.subheader("📉 合体したグラフ")
        st.plotly_chart(merged_fig, use_container_width=True, height=550, key="merged_chart_view")
else:
    st.info("データがまだ登録されていません。まずは上のフォームからデータを追加してください。")
