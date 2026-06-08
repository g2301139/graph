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
if "editing_idx" not in st.session_state:
    st.session_state.editing_idx = None

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

# 登録データの一覧表示と編集トリガー
if st.session_state.datasets:
    st.subheader("現在登録されているデータ一覧")
    cols = st.columns(len(st.session_state.datasets) + 1)
    for idx, dataset in enumerate(st.session_state.datasets):
        with cols[idx]:
            st.info(f"📁 {dataset['name']} ({len(dataset['df'])}行)")
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button(f"✏️ 編集", key=f"edit_trigger_{idx}"):
                    st.session_state.editing_idx = idx
            with btn_col2:
                if st.button(f"❌ 削除", key=f"del_{idx}"):
                    if st.session_state.editing_idx == idx:
                        st.session_state.editing_idx = None
                    st.session_state.datasets.pop(idx)
                    st.rerun()

    # --- データ編集用のポップアップエリア ---
    if st.session_state.editing_idx is not None:
        edit_idx = st.session_state.editing_idx
        if edit_idx < len(st.session_state.datasets):
            st.markdown("---")
            st.markdown(f"### ✏️ データの編集: 「{st.session_state.datasets[edit_idx]['name']}」")
            
            new_name = st.text_input("データセットの名前を変更", value=st.session_state.datasets[edit_idx]['name'], key="edit_name_input")
            
            st.write("セルをダブルクリックすると数値を直接編集できます。行の追加や削除も可能です。")
            updated_df = st.data_editor(
                st.session_state.datasets[edit_idx]['df'],
                use_container_width=True,
                num_rows="dynamic",
                key="data_matrix_editor"
            )
            
            save_col1, save_col2, _ = st.columns([1, 1, 4])
            with save_col1:
                if st.button("💾 変更を保存する", type="primary", key="save_edit_btn"):
                    st.session_state.datasets[edit_idx]['name'] = new_name
                    st.session_state.datasets[edit_idx]['df'] = updated_df
                    st.session_state.editing_idx = None
                    st.success("データを更新しました！")
                    st.rerun()
            with save_col2:
                if st.button("キャンセル", key="cancel_edit_btn"):
                    st.session_state.editing_idx = None
                    st.rerun()
        else:
            st.session_state.editing_idx = None

# 共通で使う補助関数
def get_trendline_data(dataframe, x_col, y_col):
    try:
        x_vals = pd.to_numeric(dataframe[x_col]).values
        y_vals = pd.to_numeric(dataframe[y_col]).values
        ridx = np.isfinite(x_vals) & np.isfinite(y_vals)
        a, b = np.polyfit(x_vals[ridx], y_vals[ridx], 1)
        return np.array([min(x_vals), max(x_vals)]), a * np.array([min(x_vals), max(x_vals)]) + b
    except: return None, None

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
                custom_x_label = st.text_input("横軸（X軸）の表示名", value=x_axis, key=f"label_x_{idx}")
            with label_col2:
                default_y_label = ", ".join(y_axes) if y_axes else "値"
                custom_y_label = st.text_input("縦軸（Y軸）の表示名", value=default_y_label, key=f"label_y_{idx}")

            # 線の引き方・凡例名の個別設定
            line_styles_config = {}
            legend_names_config = {}
            if y_axes:
                st.markdown("##### 表示スタイルと右側の表示名（凡例）の設定")
                for y_col in y_axes:
                    st.markdown(f"**■ 項目: {y_col}**")
                    style_col, name_col = st.columns(2)
                    with style_col:
                        line_style = st.selectbox(
                            f"「{y_col}」の表示スタイル", 
                            options=["点（マーカー）のみ", "直線（線のみ）", "曲線（滑らかな線のみ）", "点と直線", "点と曲線", "トレンド線（直線）"], 
                            index=4, 
                            key=f"style_{idx}_{y_col}"
                        )
                        line_styles_config[y_col] = line_style
                    
                    with name_col:
                        legend_names_config[y_col] = {}
                        
                        if color_axis != "なし":
                            for cat in df[color_axis].unique():
                                base_name = f"{dataset['name']} ({cat})"
                                if line_style in ["点と直線", "点と曲線"]:
                                    suffix = "直線" if line_style == "点と直線" else "曲線"
                                    legend_names_config[y_col][f"marker_{cat}"] = st.text_input(f"右側の表示名（点）: {y_col} [{cat}]", value=f"{base_name} (点)", key=f"legname_m_{idx}_{y_col}_{cat}")
                                    legend_names_config[y_col][f"line_{cat}"] = st.text_input(f"右側の表示名（{suffix}）: {y_col} [{cat}]", value=f"{base_name} ({suffix})", key=f"legname_l_{idx}_{y_col}_{cat}")
                                elif line_style == "トレンド線（直線）":
                                    legend_names_config[y_col][f"marker_{cat}"] = st.text_input(f"右側の表示名（点）: {y_col} [{cat}]", value=f"{base_name}", key=f"legname_m_{idx}_{y_col}_{cat}")
                                    legend_names_config[y_col][f"line_{cat}"] = st.text_input(f"右側の表示名（トレンド線）: {y_col} [{cat}]", value=f"{base_name} (トレンド線)", key=f"legname_l_{idx}_{y_col}_{cat}")
                                elif line_style == "点（マーカー）のみ":
                                    legend_names_config[y_col][f"marker_{cat}"] = st.text_input(f"右側の表示名（点）: {y_col} [{cat}]", value=base_name, key=f"legname_m_{idx}_{y_col}_{cat}")
                                else:
                                    legend_names_config[y_col][f"line_{cat}"] = st.text_input(f"右側の表示名（線）: {y_col} [{cat}]", value=base_name, key=f"legname_l_{idx}_{y_col}_{cat}")
                        else:
                            base_name = f"{dataset['name']}"
                            if line_style in ["点と直線", "点と曲線"]:
                                suffix = "直線" if line_style == "点と直線" else "曲線"
                                legend_names_config[y_col]["marker"] = st.text_input(f"右側の表示名（点）", value=f"{base_name} (点)", key=f"legname_m_{idx}_{y_col}")
                                legend_names_config[y_col]["line"] = st.text_input(f"右側の表示名（{suffix}）", value=f"{base_name} ({suffix})", key=f"legname_l_{idx}_{y_col}")
                            elif line_style == "トレンド線（直線）":
                                legend_names_config[y_col]["marker"] = st.text_input(f"右側の表示名（点）", value=f"{base_name}", key=f"legname_m_{idx}_{y_col}")
                                legend_names_config[y_col]["line"] = st.text_input(f"右側の表示名（トレンド線）", value=f"{base_name} (トレンド線)", key=f"legname_l_{idx}_{y_col}")
                            elif line_style == "点（マーカー）のみ":
                                legend_names_config[y_col]["marker"] = st.text_input(f"右側の表示名（点）", value=base_name, key=f"legname_m_{idx}_{y_col}")
                            else:
                                legend_names_config[y_col]["line"] = st.text_input(f"右側の表示名（線）", value=base_name, key=f"legname_l_{idx}_{y_col}")

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
                    names = legend_names_config.get(y_axis, {})
                    shape_mode = "spline" if "曲線" in selected_style else "linear"
                        
                    if color_axis != "なし":
                        for cat in df[color_axis].unique():
                            sub_df = df[df[color_axis] == cat]
                            color = color_cycle[c_idx % len(color_cycle)]
                            c_idx += 1
                            
                            if selected_style == "点（マーカー）のみ":
                                fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="markers", marker=dict(size=10, color=color), name=names.get(f"marker_{cat}")))
                            elif selected_style in ["直線（線のみ）", "曲線（滑らかな線のみ）"]:
                                fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="lines", line=dict(shape=shape_mode, color=color), name=names.get(f"line_{cat}")))
                            elif selected_style in ["点と直線", "点と曲線"]:
                                fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="markers", marker=dict(size=10, color=color), name=names.get(f"marker_{cat}")))
                                fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="lines", line=dict(shape=shape_mode, color=color), name=names.get(f"line_{cat}")))
                            elif selected_style == "トレンド線（直線）":
                                fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="markers", marker=dict(size=10, color=color), name=names.get(f"marker_{cat}")))
                                x_t, y_t = get_trendline_data(sub_df, x_axis, y_axis)
                                if x_t is not None: fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=color), name=names.get(f"line_{cat}")))
                    else:
                        color = color_cycle[c_idx % len(color_cycle)]
                        c_idx += 1
                        
                        if selected_style == "点（マーカー）のみ":
                            fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="markers", marker=dict(size=10, color=color), name=names.get("marker")))
                        elif selected_style in ["直線（線のみ）", "曲線（滑らかな線のみ）"]:
                            fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="lines", line=dict(shape=shape_mode, color=color), name=names.get("line")))
                        elif selected_style in ["点と直線", "点と曲線"]:
                            fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="markers", marker=dict(size=10, color=color), name=names.get("marker")))
                            fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="lines", line=dict(shape=shape_mode, color=color), name=names.get("line")))
                        elif selected_style == "トレンド線（直線）":
                            fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="markers", marker=dict(size=10, color=color), name=names.get("marker")))
                            x_t, y_t = get_trendline_data(df, x_axis, y_axis)
                            if x_t is not None: fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=color), name=names.get("line")))
                
                fig.update_layout(
                    title=dict(text=f"📊 グラフ: {dataset['name']}", font=dict(size=18)),
                    xaxis=dict(title=custom_x_label, tickformat="f"), 
                    yaxis=dict(title=custom_y_label, tickformat="f"), 
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
        
        setting_col1, setting_col2 = st.columns(2)
        with setting_col1:
            integrate_scales = st.checkbox("ｙ軸を固定して合体する", value=False)
            
        with setting_col2:
            custom_x_range_enabled = st.checkbox("横軸（X軸）の表示範囲を手動で設定する", value=False)
            if custom_x_range_enabled:
                range_col1, range_col2 = st.columns(2)
                with range_col1:
                    x_min_val = st.number_input("横軸の最小値 (Min)", value=0.0, step=1.0, key="x_range_min")
                with range_col2:
                    x_max_val = st.number_input("横軸の最大値 (Max)", value=5000000.0, step=1.0, key="x_range_max")

        st.markdown("✏️ **合体グラフの軸ラベル・表示範囲（最大・最小）の設定**")
        
        first_cfg = configs.get(selected_indices[0]) if selected_indices else None
        default_merged_x_label = first_cfg["custom_x_label"] if first_cfg else "共通横軸 (X)"
        merged_x_title = st.text_input("合体グラフの横軸（X軸）名", value=default_merged_x_label, key="merged_label_x")

        custom_axis_titles = {}
        custom_y_ranges = {}
        axis_label_idx = 0
        
        for loop_count, idx in enumerate(selected_indices):
            dataset = st.session_state.datasets[idx]
            cfg = configs.get(idx)
            if not cfg or not cfg["y_axes"]: continue
            
            default_title = cfg["custom_y_label"]
            
            # 各縦軸の設定フォームを作る
            if loop_count == 0:
                label_text = "共通の縦軸名（Y軸）" if integrate_scales else f"ベースとなる左側の縦軸名（第1 Y軸: {dataset['name']} 用）"
                st.markdown(f"**■ {label_text}**")
                title_col, range_check_col, min_col, max_col = st.columns([2, 1, 1, 1])
                with title_col:
                    custom_axis_titles["y"] = st.text_input("軸の表示名", value="共通縦軸 (Y)" if integrate_scales else default_title, key=f"custom_title_y_{idx}", label_visibility="collapsed")
                with range_check_col:
                    y_range_enabled = st.checkbox("範囲を手動指定", value=False, key=f"y_range_enable_{idx}")
                with min_col:
                    y_min = st.number_input("最小値", value=0.0, key=f"y_min_{idx}", disabled=not y_range_enabled)
                with max_col:
                    y_max = st.number_input("最大値", value=100.0, key=f"y_max_{idx}", disabled=not y_range_enabled)
                if y_range_enabled:
                    custom_y_ranges["y"] = [y_min, y_max]
                    
            else:
                if not integrate_scales:
                    axis_label_idx += 1
                    label_text = f"右側に追加される縦軸名（第{axis_label_idx + 1} Y軸: {dataset['name']} 用）"
                    st.markdown(f"**■ {label_text}**")
                    title_col, range_check_col, min_col, max_col = st.columns([2, 1, 1, 1])
                    with title_col:
                        custom_axis_titles[f"y_axis_{idx}"] = st.text_input("軸の表示名", value=default_title, key=f"custom_title_y_{idx}", label_visibility="collapsed")
                    with range_check_col:
                        y_range_enabled = st.checkbox("範囲を手動指定", value=False, key=f"y_range_enable_{idx}")
                    with min_col:
                        y_min = st.number_input("最小値", value=0.0, key=f"y_min_{idx}", disabled=not y_range_enabled)
                    with max_col:
                        y_max = st.number_input("最大値", value=100.0, key=f"y_max_{idx}", disabled=not y_range_enabled)
                    if y_range_enabled:
                        custom_y_ranges[f"y_axis_{idx}"] = [y_min, y_max]

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
                xaxis_dict = dict(title=merged_x_title, side="bottom", tickformat="f")
                if custom_x_range_enabled:
                    xaxis_dict["range"] = [x_min_val, x_max_val]
                update_layout_args["xaxis"] = xaxis_dict
            
            if loop_count == 0 or integrate_scales:
                yaxis_id = "y"
                if loop_count == 0:
                    y_dict = dict(title=custom_axis_titles.get("y", "縦軸"), side="left", tickformat="f")
                    if "y" in custom_y_ranges:
                        y_dict["range"] = custom_y_ranges["y"]
                    update_layout_args["yaxis"] = y_dict
            else:
                extra_y_count += 1
                yaxis_id = f"y{extra_y_count + 1}"
                
                # 【修正ポイント】右側の軸同士が重ならないよう、1軸ごとに0.085ずつ外側にシフト。
                # anchor="free" に設定することで、positionの数値通りに配置されます。
                pos_offset = 1.0 + ((extra_y_count - 1) * 0.085)
                
                y_dict = dict(
                    title=dict(text=custom_axis_titles.get(f"y_axis_{idx}", f"縦軸 {extra_y_count + 1}")),
                    overlaying="y",
                    side="right", 
                    anchor="free",
                    position=pos_offset,
                    tickformat="f"
                )
                if f"y_axis_{idx}" in custom_y_ranges:
                    y_dict["range"] = custom_y_ranges[f"y_axis_{idx}"]
                    
                update_layout_args[f"yaxis{extra_y_count + 1}"] = y_dict

            # データのプロット
            for y_axis in cfg["y_axes"]:
                selected_style = line_styles.get(y_axis)
                names = legend_names.get(y_axis, {})
                trace_xaxis = "x" if xaxis_id == "x" else xaxis_id
                trace_yaxis = "y" if yaxis_id == "y" else yaxis_id
                
                shape_mode = "spline" if "曲線" in selected_style else "linear"
                
                if color_axis != "なし":
                    for cat in df[color_axis].unique():
                        sub_df = df[df[color_axis] == cat]
                        color = color_cycle_merged[merged_color_idx % len(color_cycle_merged)]
                        merged_color_idx += 1

                        if selected_style == "点（マーカー）のみ":
                            merged_fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="markers", marker=dict(size=10, color=color), name=names.get(f"marker_{cat}"), xaxis=trace_xaxis, yaxis=trace_yaxis))
                        elif selected_style in ["直線（線のみ）", "曲線（滑らかな線のみ）"]:
                            merged_fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="lines", line=dict(shape=shape_mode, color=color), name=names.get(f"line_{cat}"), xaxis=trace_xaxis, yaxis=trace_yaxis))
                        elif selected_style in ["点と直線", "点と曲線"]:
                            merged_fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="markers", marker=dict(size=10, color=color), name=names.get(f"marker_{cat}"), xaxis=trace_xaxis, yaxis=trace_yaxis))
                            merged_fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="lines", line=dict(shape=shape_mode, color=color), name=names.get(f"line_{cat}"), xaxis=trace_xaxis, yaxis=trace_yaxis))
                        elif selected_style == "トレンド線（直線）":
                            merged_fig.add_trace(go.Scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="markers", marker=dict(size=10, color=color), name=names.get(f"marker_{cat}"), xaxis=trace_xaxis, yaxis=trace_yaxis))
                            x_t, y_t = get_trendline_data(sub_df, x_axis, y_axis)
                            if x_t is not None: merged_fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=color), name=names.get(f"line_{cat}"), xaxis=trace_xaxis, yaxis=trace_yaxis))
                else:
                    color = color_cycle_merged[merged_color_idx % len(color_cycle_merged)]
                    merged_color_idx += 1

                    if selected_style == "点（マーカー）のみ":
                        merged_fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="markers", marker=dict(size=10, color=color), name=names.get("marker"), xaxis=trace_xaxis, yaxis=trace_yaxis))
                    elif selected_style in ["直線（線のみ）", "曲線（滑らかな線のみ）"]:
                        merged_fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="lines", line=dict(shape=shape_mode, color=color), name=names.get("line"), xaxis=trace_xaxis, yaxis=trace_yaxis))
                    elif selected_style in ["点と直線", "点と曲線"]:
                        merged_fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="markers", marker=dict(size=10, color=color), name=names.get("marker"), xaxis=trace_xaxis, yaxis=trace_yaxis))
                        merged_fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="lines", line=dict(shape=shape_mode, color=color), name=names.get("line"), xaxis=trace_xaxis, yaxis=trace_yaxis))
                    elif selected_style == "トレンド線（直線）":
                        merged_fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="markers", marker=dict(size=10, color=color), name=names.get("marker"), xaxis=trace_xaxis, yaxis=trace_yaxis))
                        x_t, y_t = get_trendline_data(df, x_axis, y_axis)
                        if x_t is not None: merged_fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=color), name=names.get("line"), xaxis=trace_xaxis, yaxis=trace_yaxis))

        # 【修正ポイント】右側にはみ出る複数の軸が途切れないよう、軸の数に応じて右余白（r）を動的に広げる
        right_margin = 60 + (max(0, extra_y_count) * 85)
        update_layout_args["margin"] = dict(l=80, r=right_margin)

        # レイアウト適用
        merged_fig.update_layout(**update_layout_args)

        st.subheader("📉 合体したグラフ")
        st.plotly_chart(merged_fig, use_container_width=True, height=550, key="merged_chart_view")
else:
    st.info("データがまだ登録されていません。まずは上のフォームからデータを追加してください。")
