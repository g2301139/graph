import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from io import StringIO
import re

st.set_page_config(page_title="マルチデータ・万能グラフ作成アプリ", layout="wide")

st.title("📊 高機能マルチグラフ作成Webアプリ")
st.write("複数のデータを個別に入力・設定し、合体時には指定したデータ同士の縦軸・横軸を自由に選んで統合できるようになりました。")

# -----------------------------------------------------------------------------
# セッション状態（State）の初期化
# -----------------------------------------------------------------------------
if "datasets" not in st.session_state:
    st.session_state.datasets = []
if "editing_idx" not in st.session_state:
    st.session_state.editing_idx = None

default_paste_data = (
    "X軸データ\t売上\t利益\t目標値\tカテゴリー\n"
    "1000000\t10000000\t2\t8\tA\n"
    "2000000\t12000000\t5\t10\tB\n"
    "3000000\t18000000\t4\t15\tA\n"
    "4000000\t20000000\t8\t18\tB\n"
    "5000000\t26000000\t7\t22\tA"
)
if "input_buffer" not in st.session_state:
    st.session_state.input_buffer = default_paste_data
if "input_name" not in st.session_state:
    st.session_state.input_name = f"データセット {len(st.session_state.datasets) + 1}"

# トレンド線（近似曲線）を計算するヘルパー関数
def calculate_trend_line(x_series, y_series, degree=1):
    try:
        mask = ~np.isnan(x_series) & ~np.isnan(y_series)
        x_clean = x_series[mask].astype(float)
        y_clean = y_series[mask].astype(float)
        if len(x_clean) < degree + 1:
            return x_series, y_series
        z = np.polyfit(x_clean, y_clean, degree)
        p = np.poly1d(z)
        x_trend = np.linspace(x_clean.min(), x_clean.max(), 100)
        y_trend = p(x_trend)
        return x_trend, y_trend
    except:
        return x_series, y_series

# -----------------------------------------------------------------------------
# 1. データの入力と管理
# -----------------------------------------------------------------------------
st.header("1. データの入力と管理")

with st.form("add_data_form", clear_on_submit=False):
    dataset_name = st.text_input("データの名前", value=st.session_state.input_name, key="form_dataset_name")
    paste_input = st.text_area("Excelやスプレッドシートからデータをコピーし、下の枠内に貼り付けてください：", value=st.session_state.input_buffer, height=150, key="form_paste_input")
    submit_button = st.form_submit_button("📥 このデータをアプリに追加する")

st.session_state.input_buffer = paste_input
st.session_state.input_name = dataset_name

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
        
        st.session_state.datasets.append({"name": dataset_name, "df": new_df})
        st.success(f"「{dataset_name}」を追加しました！")
        st.session_state.input_buffer = default_paste_data
        st.session_state.input_name = f"データセット {len(st.session_state.datasets) + 1}"
        st.rerun()
    except Exception as e:
        st.error(f"データの読み込みに失敗しました。エラー: {e}")

if st.session_state.datasets:
    st.subheader("現在登録されているデータ一覧")
    cols = st.columns(len(st.session_state.datasets) + 1)
    for idx, dataset in enumerate(st.session_state.datasets):
        with cols[idx]:
            st.info(f"📁 {dataset['name']} ({len(dataset['df'])}行)")
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button(f"✏️ 編集", key=f"edit_trigger_{idx}"): st.session_state.editing_idx = idx
            with btn_col2:
                if st.button(f"❌ 削除", key=f"del_{idx}"):
                    if st.session_state.editing_idx == idx: st.session_state.editing_idx = None
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
            with col1: x_axis = st.selectbox("X軸データ列を選択", options=columns, index=0, key=f"x_{idx}")
            with col2:
                default_y = [c for c in columns[1:] if c != "カテゴリー"]
                if not default_y: default_y = [columns[0]]
                y_axes = st.multiselect("Y軸データ列を選択", options=columns, default=default_y, key=f"y_{idx}")
            with col3: color_axis = st.selectbox("色分け列（オプション）", options=["なし"] + columns, index=0, key=f"color_{idx}")

            label_col1, label_col2 = st.columns(2)
            with label_col1: custom_x_label = st.text_input("横軸の表示名", value=x_axis, key=f"label_x_{idx}")
            with label_col2:
                default_y_label = ", ".join(y_axes) if y_axes else "値"
                custom_y_label = st.text_input("全体の縦軸の表示名", value=default_y_label, key=f"label_y_{idx}")

            st.markdown("✏️ **個別グラフの各縦軸詳細設定（軸名・範囲・形状）**")
            single_y_titles = {}
            single_y_mins = {}
            single_y_maxs = {}
            single_y_shapes = {}
            
            if y_axes:
                for y_loop, y_col in enumerate(y_axes):
                    if y_loop == 0: st.markdown(f"##### 🔹 第1縦軸（左側）: 「{y_col}」用")
                    else: st.markdown(f"##### 🔸 第{y_loop + 1}縦軸（右側）: 「{y_col}」用")
                        
                    t_col, shape_col, min_col, max_col = st.columns([2, 2, 1, 1])
                    with t_col: single_y_titles[y_col] = st.text_input(f"軸名 [{y_col}]", value=y_col, key=f"single_title_{idx}_{y_col}")
                    with shape_col:
                        single_y_shapes[y_col] = st.selectbox(
                            f"グラフの形状",
                            options=["直線（全点結ぶ・マーカーあり）", "なめらかな曲線（全点結ぶ）", "点（マーカー）のみ", "直線のみ（全点結ぶ）", "📈 トレンド線（直線：1次近似）", "📈 トレンド線（なめらかな曲線：2次近似）"],
                            index=0, key=f"single_shape_{idx}_{y_col}"
                        )
                    with min_col: single_y_mins[y_col] = st.text_input(f"最小値（空欄自動）", value="", key=f"single_min_{idx}_{y_col}")
                    with max_col: single_y_maxs[y_col] = st.text_input(f"最大値（空欄自動）", value="", key=f"single_max_{idx}_{y_col}")

            configs[idx] = {
                "x_axis": x_axis, "y_axes": y_axes, "color_axis": color_axis,
                "custom_x_label": custom_x_label, "custom_y_label": custom_y_label,
                "shapes": single_y_shapes, "titles": single_y_titles, "mins": single_y_mins, "maxs": single_y_maxs
            }

            if y_axes:
                fig = go.Figure()
                color_cycle = px.colors.qualitative.Plotly
                color_idx = 0
                single_axis_count = len(y_axes)
                left_domain_end = max(0.1, 1.0 - (max(0, single_axis_count - 1) * 0.06))
                
                fig.update_layout(
                    title=dict(text=f"📊 グラフ: {dataset['name']}", font=dict(size=18)),
                    hovermode="closest",
                    xaxis=dict(title=custom_x_label, side="bottom", tickformat="f", domain=[0.0, left_domain_end]),
                    margin=dict(l=60, r=20 + (max(0, single_axis_count - 1) * 60), t=50, b=60)
                )
                
                for y_loop, y_col in enumerate(y_axes):
                    layout_key = "yaxis" if y_loop == 0 else f"yaxis{y_loop + 1}"
                    target_yaxis_id = "y" if y_loop == 0 else f"y{y_loop + 1}"
                    axis_args = {"title": single_y_titles.get(y_col, y_col), "tickformat": "f"}
                    
                    try:
                        mn = single_y_mins.get(y_col, "").strip()
                        mx = single_y_maxs.get(y_col, "").strip()
                        if mn != "" and mx != "":
                            axis_args["range"] = [float(mn), float(mx)]
                            axis_args["autorange"] = False
                    except ValueError: pass
                    
                    if y_loop == 0: axis_args["side"] = "left"
                    else:
                        axis_args.update({"side": "right", "overlaying": "y", "anchor": "free", "position": min(1.0, 1.0 - (max(0, single_axis_count - 1 - y_loop) * 0.04))})
                    
                    fig.layout[layout_key] = axis_args
                    chosen_shape = single_y_shapes.get(y_col, "直線（全点結ぶ・マーカーあり）")
                    color = color_cycle[color_idx % len(color_cycle)]
                    color_idx += 1
                    
                    if "トレンド線" in chosen_shape:
                        degree = 1 if "1次近似" in chosen_shape else 2
                        x_t, y_t = calculate_trend_line(df[x_axis], df[y_col], degree=degree)
                        fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_col], mode="markers", marker=dict(color=color, opacity=0.4, size=7), name=f"{y_col} (元データ)", yaxis=target_yaxis_id, showlegend=False))
                        fig.add_trace(go.Scatter(x=x_t, y=y_t, mode="lines", line=dict(color=color, width=3, shape="spline" if degree==2 else "linear"), name=f"{y_col} (トレンド線)", yaxis=target_yaxis_id))
                    else:
                        line_config = dict(color=color)
                        if chosen_shape == "直線（全点結ぶ・マーカーあり）": plot_mode = "lines+markers"
                        elif chosen_shape == "なめらかな曲線（全点結ぶ）": plot_mode = "lines+markers"; line_config["shape"] = "spline"
                        elif chosen_shape == "点（マーカー）のみ": plot_mode = "markers"
                        elif chosen_shape == "直線のみ（全点結ぶ）": plot_mode = "lines"
                        else: plot_mode = "lines+markers"
                        fig.add_trace(go.Scatter(x=df[x_axis], y=df[y_col], mode=plot_mode, line=line_config, marker=dict(color=color), name=y_col, yaxis=target_yaxis_id))
                    
                st.plotly_chart(fig, use_container_width=True, key=f"single_chart_{idx}")

    # -----------------------------------------------------------------------------
    # 3. グラフの合体セクション (自由指定型マルチ軸・統合システム)
    # -----------------------------------------------------------------------------
    st.markdown("---")
    st.header("3. 🔗 グラフの合体（指定した縦軸・横軸を統合）")
    st.write("合体させたいデータを選び、それぞれ「どの横軸グループ」「どの縦軸グループ」に割り当てるか指定してください。**同じグループに設定したデータ同士は自動で軸が統合されます。**")
    
    selected_indices = []
    mapping_xaxis_grp = {} # idx -> 割り当てられたX軸グループ番号(1~4)
    mapping_yaxis_grp = {} # idx -> 割り当てられたY軸グループ番号(1~4)
    
    cb_cols = st.columns(len(st.session_state.datasets))
    for idx, dataset in enumerate(st.session_state.datasets):
        with cb_cols[idx]:
            is_checked = st.checkbox(f"合体する: {dataset['name']}", value=True, key=f"merge_cb_{idx}")
            if is_checked:
                selected_indices.append(idx)
                
                # 横軸（X軸）のグループ選択
                chosen_x = st.selectbox(
                    f"└ 🔗 横軸グループ",
                    options=["横軸 1", "横軸 2", "横軸 3", "横軸 4"],
                    index=0, # デフォルトはすべて「横軸 1」に統合
                    key=f"user_x_grp_{idx}"
                )
                mapping_xaxis_grp[idx] = int(re.search(r'\d+', chosen_x).group())
                
                # 縦軸（Y軸）のグループ選択
                chosen_y = st.selectbox(
                    f"└ 🔗 縦軸グループ",
                    options=["縦軸 1 (左側)", "縦軸 2 (右側-1)", "縦軸 3 (右側-2)", "縦軸 4 (右側-3)"],
                    index=0 if idx == 0 else min(idx, 1), # 初期値として少しばらけさせる親切設計
                    key=f"user_y_grp_{idx}"
                )
                mapping_yaxis_grp[idx] = int(re.search(r'\d+', chosen_y).group())

    if len(selected_indices) < 1:
        st.warning("合体するデータを1つ以上選択してください。")
    else:
        merged_fig = go.Figure()
        color_cycle_merged = px.colors.qualitative.Plotly
        color_idx_merged = 0
        
        # 実際にユーザーに選ばれて「稼働している」軸グループのリストを取得（重複排除）
        active_x_grps = sorted(list(set(mapping_xaxis_grp.values())))
        active_y_grps = sorted(list(set(mapping_yaxis_grp.values())))
        
        # グラフ描画エリアの左右マージン配分
        right_y_count = len([a for a in active_y_grps if a > 1])
        left_xaxis_domain = 0.07 * len([a for a in active_y_grps if a == 1]) # 左側の縦軸の数に応じた余白
        left_xaxis_domain = max(0.12, left_xaxis_domain)
        right_xaxis_domain = max(0.1, 1.0 - (right_y_count * 0.06))
        
        merged_fig.update_layout(
            hovermode="closest",
            margin=dict(l=20 + (len(active_y_grps)*40), r=20 + (right_y_count*60), t=50, b=40 + (len(active_x_grps)*40)),
        )

        # -------------------------------------------------------------------------
        # 稼働している【横軸(X軸)グループ】のレイアウト作成・登録
        # -------------------------------------------------------------------------
        plotly_x_id_map = {} # Xグループ番号 -> PlotlyのスタンスID ("x", "x2"...)
        for loop_idx, x_grp_num in enumerate(active_x_grps):
            layout_key = "xaxis" if loop_idx == 0 else f"xaxis{loop_idx + 1}"
            plotly_x_id_map[x_grp_num] = "x" if loop_idx == 0 else f"x{loop_idx + 1}"
            
            # 代表として、このグループを使う最初のデータセットの設定名を取得
            rep_idx = [i for i, g in mapping_xaxis_grp.items() if g == x_grp_num][0]
            rep_label = configs[rep_idx]["custom_x_label"]
            
            x_setup = dict(title=f"横軸グループ {x_grp_num} ({rep_label})", tickformat="f")
            
            if loop_idx == 0:
                x_setup.update(dict(side="bottom", domain=[left_xaxis_domain, right_xaxis_domain]))
            else:
                # 2つ目以降の横軸グループは上下に交互に配置をオフセット
                side_pos = "top" if loop_idx % 2 == 1 else "bottom"
                offset = (loop_idx // 2) * 0.08
                x_setup.update(dict(
                    side=side_pos, overlaying="x", anchor="free",
                    position=max(0.0, min(1.0, (0.0 - offset) if side_pos == "bottom" else (1.0 + offset)))
                ))
            merged_fig.layout[layout_key] = x_setup

        # -------------------------------------------------------------------------
        # 稼働している【縦軸(Y軸)グループ】のレイアウト作成・登録
        # -------------------------------------------------------------------------
        plotly_y_id_map = {} # Yグループ番号 -> PlotlyのスタンスID ("y", "y2"...)
        right_drawn_count = 0
        
        for loop_idx, y_grp_num in enumerate(active_y_grps):
            if y_grp_num == 1:
                layout_key = "yaxis"
                plotly_y_id_map[y_grp_num] = "y"
            else:
                right_drawn_count += 1
                layout_key = f"yaxis{right_drawn_count + 1}"
                plotly_y_id_map[y_grp_num] = f"y{right_drawn_count + 1}"
            
            # 代表として、このグループを使う最初のデータセットの設定名を取得
            rep_idx = [i for i, g in mapping_yaxis_grp.items() if g == y_grp_num][0]
            rep_label = configs[rep_idx]["custom_y_label"]
            
            y_setup = dict(title=f"縦軸グループ {y_grp_num} ({rep_label})", tickformat="f")
            
            if y_grp_num == 1:
                y_setup.update(dict(side="left", anchor="x"))
            else:
                # 軸グループ2以降は右側に順番に並べる
                y_setup.update(dict(
                    side="right", overlaying="y", anchor="free",
                    position=min(1.0, 1.0 - (max(0, right_y_count - right_drawn_count) * 0.05))
                ))
            merged_fig.layout[layout_key] = y_setup

        # -------------------------------------------------------------------------
        # データプロット（選択された全系列の描画ループ）
        # -------------------------------------------------------------------------
        for idx in selected_indices:
            dataset = st.session_state.datasets[idx]
            df = dataset["df"]
            cfg = configs.get(idx)
            if not cfg or not cfg["y_axes"]: continue

            # このデータセットが所属する「Plotly上の軸ID」を取得
            user_x_grp = mapping_xaxis_grp[idx]
            user_y_grp = mapping_yaxis_grp[idx]
            
            target_xaxis = plotly_x_id_map[user_x_grp]
            target_yaxis = plotly_y_id_map[user_y_grp]

            # ユーザーが選択したすべてのY軸（縦軸データ）をプロット
            for y_axis in cfg["y_axes"]:
                color = color_cycle_merged[color_idx_merged % len(color_cycle_merged)]
                color_idx_merged += 1
                
                chosen_shape = cfg.get("shapes", {}).get(y_axis, "直線（全点結ぶ・マーカーあり）")
                
                if "トレンド線" in chosen_shape:
                    degree = 1 if "1次近似" in chosen_shape else 2
                    x_t, y_t = calculate_trend_line(df[cfg["x_axis"]], df[y_axis], degree=degree)
                    
                    # 元データ（点）
                    merged_fig.add_trace(go.Scatter(
                        x=df[cfg["x_axis"]], y=df[y_axis], mode="markers",
                        marker=dict(color=color, opacity=0.3, size=6),
                        name=f"{dataset['name']}-{y_axis} (点)",
                        xaxis=target_xaxis, yaxis=target_yaxis, showlegend=False
                    ))
                    # 近似曲線（トレンド線）
                    merged_fig.add_trace(go.Scatter(
                        x=x_t, y=y_t, mode="lines",
                        line=dict(color=color, width=2.5, shape="spline" if degree==2 else "linear"),
                        name=f"{dataset['name']}-{y_axis} (トレンド)",
                        xaxis=target_xaxis, yaxis=target_yaxis
                    ))
                else:
                    line_config_merged = dict(color=color)
                    if chosen_shape == "直線（全点結ぶ・マーカーあり）": m_mode = "lines+markers"
                    elif chosen_shape == "なめらかな曲線（全点結ぶ）": m_mode = "lines+markers"; line_config_merged["shape"] = "spline"
                    elif chosen_shape == "点（マーカー）のみ": m_mode = "markers"
                    elif chosen_shape == "直線のみ（全点結ぶ）": m_mode = "lines"
                    else: m_mode = "lines+markers"
                    
                    merged_fig.add_trace(go.Scatter(
                        x=df[cfg["x_axis"]], y=df[y_axis], mode=m_mode,
                        line=line_config_merged, marker=dict(color=color),
                        name=f"{dataset['name']}-{y_axis}",
                        xaxis=target_xaxis, yaxis=target_yaxis
                    ))

        st.subheader("📉 条件指定・軸統合合体グラフ")
        st.plotly_chart(merged_fig, use_container_width=True, height=650, key="final_flexible_merged_chart")
else:
    st.info("データがまだ登録されていません。まずは上のフォームからデータを追加してください。")
