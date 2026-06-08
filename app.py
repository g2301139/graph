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
    dataset_name = st.text_input("データの名前", value=f"データセット {len(st.session_state.datasets) + 1}")
    paste_input = st.text_area(
        "Excelやスプレッドシートからデータをコピーし、下の枠内に貼り付けてください：",
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

# 登録データの一覧表示
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

    if st.session_state.editing_idx is not None:
        edit_idx = st.session_state.editing_idx
        if edit_idx < len(st.session_state.datasets):
            st.markdown("---")
            st.markdown(f"### ✏️ データの編集: 「{st.session_state.datasets[edit_idx]['name']}」")
            new_name = st.text_input("データセットの名前を変更", value=st.session_state.datasets[edit_idx]['name'], key="edit_name_input")
            updated_df = st.data_editor(st.session_state.datasets[edit_idx]['df'], use_container_width=True, num_rows="dynamic", key="data_matrix_editor")
            
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
    tabs = st.tabs([d["name"] for d in st.session_state.datasets])
    
    for idx, dataset in enumerate(st.session_state.datasets):
        with tabs[idx]:
            df = dataset["df"]
            columns = df.columns.tolist()
            
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                x_axis = st.selectbox("X軸データ列を選択", options=columns, index=0, key=f"x_{idx}")
            with col2:
                default_y = [c for c in columns[1:] if c != "カテゴリー"]
                if not default_y: default_y = [columns[0]]
                y_axes = st.multiselect("Y軸データ列を選択", options=columns, default=default_y, key=f"y_{idx}")
            with col3:
                color_axis = st.selectbox("色分け列（オプション）", options=["なし"] + columns, index=0, key=f"color_{idx}")

            label_col1, label_col2 = st.columns(2)
            with label_col1:
                custom_x_label = st.text_input("横軸の表示名", value=x_axis, key=f"label_x_{idx}")
            with label_col2:
                default_y_label = ", ".join(y_axes) if y_axes else "値"
                custom_y_label = st.text_input("縦軸の表示名", value=default_y_label, key=f"label_y_{idx}")

            line_styles_config = {}
            legend_names_config = {}
            if y_axes:
                for y_col in y_axes:
                    style_col, name_col = st.columns(2)
                    with style_col:
                        line_style = st.selectbox(f"「{y_col}」のスタイル", options=["点（マーカー）のみ", "直線（線のみ）", "曲線（滑らかな線のみ）", "点と直線", "点と曲線", "トレンド線（直線）"], index=3, key=f"style_{idx}_{y_col}")
                        line_styles_config[y_col] = line_style
                    with name_col:
                        legend_names_config[y_col] = {}
                        base_name = f"{dataset['name']}"
                        legend_names_config[y_col]["marker"] = st.text_input(f"凡例名（点）: {y_col}", value=f"{base_name} ({y_col})", key=f"legname_m_{idx}_{y_col}")

            configs[idx] = {
                "x_axis": x_axis, "y_axes": y_axes, "color_axis": color_axis,
                "line_styles": line_styles_config, "legend_names": legend_names_config,
                "custom_x_label": custom_x_label, "custom_y_label": custom_y_label
            }

            if y_axes:
                fig = go.Figure()
                for y_axis in y_axes:
                    fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_axis], mode="lines+markers", name=y_axis))
                fig.update_layout(xaxis=dict(title=custom_x_label, tickformat="f"), yaxis=dict(title=custom_y_label, tickformat="f"))
                st.plotly_chart(fig, use_container_width=True, key=f"single_chart_{idx}")

    # -----------------------------------------------------------------------------
    # 3. グラフの合体セクション
    # -----------------------------------------------------------------------------
    st.markdown("---")
    st.header("3. 🔗 グラフの合体（重ね合わせ表示）")
    
    selected_indices = []
    cb_cols = st.columns(len(st.session_state.datasets))
    for idx, dataset in enumerate(st.session_state.datasets):
        with cb_cols[idx]:
            if st.checkbox(f"合体する: {dataset['name']}", value=True, key=f"merge_cb_{idx}"):
                selected_indices.append(idx)

    if len(selected_indices) < 1:
        st.warning("合体するデータを1つ以上選択してください。")
    else:
        st.subheader("② 目盛り（スケール）と範囲・軸名の設定")
        
        setting_col1, setting_col2 = st.columns(2)
        with setting_col1:
            integrate_scales = st.checkbox("すべての縦軸（Y軸）の目盛りを1つに統合する", value=False)
        with setting_col2:
            custom_x_range_enabled = st.checkbox("横軸（X軸）の表示範囲を手動で設定する", value=False)
            x_min_val, x_max_val = 0.0, 5000000.0
            if custom_x_range_enabled:
                range_col1, range_col2 = st.columns(2)
                with range_col1: x_min_val = st.number_input("横軸 最小値", value=0.0, key="x_min")
                with range_col2: x_max_val = st.number_input("横軸 最大値", value=5000000.0, key="x_max")

        st.markdown("✏️ **各縦軸（Y軸）のラベル名と個別範囲設定（最大・最小）**")
        
        custom_axis_titles = {}
        y_min_inputs = {}
        y_max_inputs = {}
        
        axis_count = 0
        for loop_count, idx in enumerate(selected_indices):
            dataset = st.session_state.datasets[idx]
            cfg = configs.get(idx)
            if not cfg or not cfg["y_axes"]: continue
            
            # 軸ごとの一意のキー文字列を定義
            axis_key = "y" if (loop_count == 0 or integrate_scales) else f"y_{idx}"
            
            if loop_count == 0:
                st.markdown(f"##### 🔹 第1縦軸（左側）: {dataset['name']} 用")
                t_col, min_col, max_col = st.columns([2, 1, 1])
                with t_col:
                    custom_axis_titles[axis_key] = st.text_input("軸の表示名", value="共通縦軸 (Y)" if integrate_scales else cfg["custom_y_label"], key=f"title_{axis_key}")
                with min_col:
                    y_min_inputs[axis_key] = st.text_input("最小値（自動の場合は空欄）", value="", key=f"min_in_{axis_key}")
                with max_col:
                    y_max_inputs[axis_key] = st.text_input("最大値（自動の場合は空欄）", value="", key=f"max_in_{axis_key}")
                axis_count += 1
            elif not integrate_scales:
                st.markdown(f"##### 🔸 第{axis_count + 1}縦軸（右側並び）: {dataset['name']} 用")
                t_col, min_col, max_col = st.columns([2, 1, 1])
                with t_col:
                    custom_axis_titles[axis_key] = st.text_input("軸の表示名", value=cfg["custom_y_label"], key=f"title_{axis_key}")
                with min_col:
                    y_min_inputs[axis_key] = st.text_input("最小値（自動の場合は空欄）", value="", key=f"min_in_{axis_key}")
                with max_col:
                    y_max_inputs[axis_key] = st.text_input("最大値（自動の場合は空欄）", value="", key=f"max_in_{axis_key}")
                axis_count += 1

        # グラフ描画ロジック開始
        merged_fig = go.Figure()
        color_cycle = px.colors.qualitative.Plotly
        color_idx = 0
        
        layout_config = {
            "hovermode": "closest",
            "margin": dict(l=80, r=50 + (max(0, axis_count - 1) * 90), t=50, b=80)
        }

        # X軸設定
        first_cfg = configs.get(selected_indices[0])
        merged_x_title = st.text_input("合体グラフの横軸名", value=first_cfg["custom_x_label"] if first_cfg else "X軸", key="m_x_label")
        
        # 右側の軸スペースを作るためにメイングラフエリア（domain）の右端を削る
        right_bound = 1.0 - (max(0, axis_count - 1) * 0.085)
        layout_config["xaxis"] = dict(title=merged_x_title, side="bottom", tickformat="f", domain=[0, min(1.0, right_bound)])
        if custom_x_range_enabled:
            layout_config["xaxis"]["range"] = [x_min_val, x_max_val]

        # Y軸の設定とデータのマッピング
        right_axis_idx = 0
        for loop_count, idx in enumerate(selected_indices):
            dataset = st.session_state.datasets[idx]
            df = dataset["df"]
            cfg = configs.get(idx)
            if not cfg or not cfg["y_axes"]: continue

            # トレースが参照するY軸IDと、レイアウトキーを確定
            if loop_count == 0 or integrate_scales:
                axis_id = "y"
                layout_key = "yaxis"
            else:
                right_axis_idx += 1
                axis_id = f"y{right_axis_idx + 1}"
                layout_key = f"yaxis{right_axis_idx + 1}"

            axis_key = "y" if (loop_count == 0 or integrate_scales) else f"y_{idx}"

            # レイアウト初期化（まだ未設定の場合のみ）
            if layout_key not in layout_config:
                axis_setup = dict(
                    title=custom_axis_titles.get(axis_key, "値"),
                    tickformat="f"
                )
                
                # 手動の最大値・最小値をパースして適用
                try:
                    mn = y_min_inputs.get(axis_key, "").strip()
                    mx = y_max_inputs.get(axis_key, "").strip()
                    if mn != "" and mx != "":
                        axis_setup["range"] = [float(mn), float(mx)]
                        axis_setup["autorange"] = False
                except ValueError:
                    pass

                if loop_count == 0 or integrate_scales:
                    axis_setup["side"] = "left"
                else:
                    # 右側に並べる。絶対に重ならないようpositionを1軸ごとに外へずらす
                    axis_setup.update(dict(
                        side="right",
                        overlaying="y",
                        anchor="free",
                        position=1.0 + ((right_axis_idx - 1) * 0.085)
                    ))
                
                layout_config[layout_key] = axis_setup

            # トレース（線・点）を追加
            for y_axis in cfg["y_axes"]:
                color = color_cycle[color_idx % len(color_cycle)]
                color_idx += 1
                
                merged_fig.add_trace(go.Scatter(
                    x=df[cfg["x_axis"]],
                    y=df[y_axis],
                    mode="lines+markers",
                    line=dict(color=color),
                    marker=dict(color=color),
                    name=f"{dataset['name']}-{y_axis}",
                    yaxis=axis_id
                ))

        merged_fig.update_layout(**layout_config)
        st.subheader("📉 合体したグラフ")
        st.plotly_chart(merged_fig, use_container_width=True, height=600, key="final_merged_chart")
