import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from io import StringIO

st.set_page_config(page_title="万能グラフ作成アプリ", layout="wide")

st.title("📊 高機能グラフ作成Webアプリ")
st.write("すべての縦軸を右側に統一し、軸の名前と数を完全にカスタマイズできるようになりました。")

# -----------------------------------------------------------------------------
# 1. データ入力セクション
# -----------------------------------------------------------------------------
st.header("1. データの入力")

default_paste_data = (
    "X軸データ\t売上\t利益\tカテゴリー\n"
    "1\t10\t2\tA\n"
    "2\t12\t5\tB\n"
    "3\t18\t4\tA\n"
    "4\t20\t8\tB\n"
    "5\t26\t7\tA"
)

paste_input = st.text_area(
    "Excelやスプレッドシートからデータをコピーし、下の枠内に貼り付けてください（Ctrl+V）：",
    value=default_paste_data,
    height=180
)

try:
    df = pd.read_csv(StringIO(paste_input), sep='\t')
    if len(df.columns) == 1 and ',' in paste_input:
        df = pd.read_csv(StringIO(paste_input), sep=',')
        
    st.subheader("現在のデータ確認")
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"データの読み込みに失敗しました。エラー: {e}")
    df = pd.DataFrame()

# -----------------------------------------------------------------------------
# 2. グラフの設定セクション
# -----------------------------------------------------------------------------
if not df.empty:
    st.header("2. グラフの設定")
    columns = df.columns.tolist()

    if len(columns) < 2:
        st.error("データを2列以上入力してください。")
    else:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            x_axis = st.selectbox("X軸（横軸）を選択", options=columns, index=0)
        with col2:
            y_axes = st.multiselect("データとして使う列を選択 ※複数選択可能", options=columns, default=[columns[1]])
        with col3:
            color_axis = st.selectbox("色分けする列（オプション）", options=["なし"] + columns, index=0)

        # ★★★ 新機能：縦軸の名前と数をユーザーが変更できる設定 ★★★
        st.subheader("縦軸（Y軸）のカスタマイズ設定")
        
        # 最初の初期値として、選んだY軸の数をベースにする
        num_axes_default = len(y_axes) if y_axes else 1
        
        # 軸の数を変更できるようにする
        num_custom_axes = st.number_input("作成する縦軸の数（名前の数）", min_value=1, max_value=10, value=num_axes_default)
        
        # 各軸の名前と、どのデータ列を割り当てるかをユーザーが入力・選択する
        custom_axes_config = []
        st.write("各軸の名前を設定し、右側に並べる順にデータを割り当ててください：")
        
        # 軸の数だけ入力欄を横並び、またはリストで作成
        for idx in range(int(num_custom_axes)):
            ax_col1, ax_col2 = st.columns([1, 2])
            with ax_col1:
                # 初期値の名前は自動。ユーザーが自由に変えられます
                default_name = y_axes[idx] if idx < len(y_axes) else f"カスタム軸 {idx+1}"
                axis_name = st.text_input(f"軸 {idx+1} の名前", value=default_name, key=f"ax_name_{idx}")
            with ax_col2:
                default_select = [y_axes[idx]] if idx < len(y_axes) else [columns[1]]
                selected_cols = st.multiselect(f"軸「{axis_name}」に担当させるデータ列", options=columns, default=default_select, key=f"ax_cols_{idx}")
            
            custom_axes_config.append({
                "name": axis_name,
                "columns": selected_cols
            })

        # 線の引き方
        st.subheader("表示する線の選択")
        col_show1, col_show2 = st.columns(2)
        with col_show1:
            show_trend = st.checkbox("全体の平均を通る一直線（トレンド線）を表示する", value=False)
        with col_show2:
            show_curve = st.checkbox("数値をみて自動判定した線（各点を通る直線または曲線）を表示する", value=False)

        # 軸の最大値・最小値の設定
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

        fig = px.line()
        color_cycle = px.colors.qualitative.Plotly
        color_idx = 0

        # トレンド線計算
        def get_trendline_data(dataframe, x_col, y_col):
            try:
                x_vals = pd.to_numeric(dataframe[x_col]).values
                y_vals = pd.to_numeric(dataframe[y_col]).values
                idx = np.isfinite(x_vals) & np.isfinite(y_vals)
                a, b = np.polyfit(x_vals[idx], y_vals[idx], 1)
                x_trend = np.array([min(x_vals), max(x_vals)])
                y_trend = a * x_trend + b
                return x_trend, y_trend
            except:
                return None, None

        # 形状自動判定
        def determine_shape(dataframe, x, y):
            try:
                x_val = pd.to_numeric(dataframe[x]).values
                y_val = pd.to_numeric(dataframe[y]).values
                if len(x_val) < 3: return "linear"
                slopes = np.diff(y_val) / np.diff(x_val)
                return "linear" if np.var(np.diff(slopes)) < 1e-5 else "spline"
            except:
                return "linear"

        # レイアウト保持用の辞書（すべて右側に寄せる設定を動的に作る）
        layout_kwargs = {
            "xaxis": dict(title=x_axis, range=x_range_input),
            "hovermode": "closest"
        }

        # ダミー用の左軸（Plotlyの仕様上、左軸を非表示にしてすべてを右側に配置します）
        layout_kwargs["yaxis"] = dict(visible=False)

        # ユーザーが設定したカスタム軸をループしてグラフを構築
        for ax_i, ax_config in enumerate(custom_axes_config):
            axis_id = f"y{ax_i + 2}" # y2, y3, y4... と右側に並べていく
            axis_name = ax_config["name"]
            target_columns = ax_config["columns"]

            # 各軸の表示設定（すべて右側「side='right'」にする）
            # 複数の軸が重ならないように位置(position)を少しずつずらす
            position_offset = 1.0 + (ax_i * 0.06) 
            
            layout_kwargs[f"yaxis{ax_i + 2}"] = dict(
                title=axis_name,
                overlaying="y",
                side="right",
                anchor="free",
                position=position_offset,
                range=y_range_input
            )

            # この軸に割り当てられたデータ列をプロット
            for y_axis in target_columns:
                if color_axis != "なし":
                    unique_categories = df[color_axis].unique()
                    for cat in unique_categories:
                        assigned_color = color_cycle[color_idx % len(color_cycle)]
                        color_idx += 1
                        sub_df = df[df[color_axis] == cat]
                        
                        # ① 点
                        fig.add_scatter(
                            x=sub_df[x_axis], y=sub_df[y_axis], mode="markers",
                            marker=dict(size=10, color=assigned_color),
                            name=f"{y_axis} [{axis_name}] ({cat})", yaxis=axis_id
                        )
                        # ② 直線
                        if show_trend:
                            x_t, y_t = get_trendline_data(sub_df, x_axis, y_axis)
                            if x_t is not None:
                                fig.add_scatter(x=x_t, y=y_t, mode="lines", line=dict(color=assigned_color, dash="dash"), name=f"{y_axis} [{axis_name}] ({cat}) [直線]", yaxis=axis_id)
                        # ③ 曲線
                        if show_curve:
                            shape_type = determine_shape(sub_df, x_axis, y_axis)
                            fig.add_scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="lines", line=dict(shape=shape_type, color=assigned_color), name=f"{y_axis} [{axis_name}] ({cat}) [各点結び]", yaxis=axis_id)
                else:
                    assigned_color = color_cycle[color_idx % len(color_cycle)]
                    color_idx += 1
                    
                    # ① 点
                    fig.add_scatter(
                        x=df[x_axis], y=df[y_axis], mode="markers",
                        marker=dict(size=10, color=assigned_color),
                        name=f"{y_axis} [{axis_name}]", yaxis=axis_id
                    )
                    # ② 直線
                    if show_trend:
                        x_t, y_t = get_trendline_data(df, x_axis, y_axis)
                        if x_t is not None:
                            fig.add_scatter(x=x_t, y=y_t, mode="lines", line=dict(color=assigned_color, dash="dash"), name=f"{y_axis} [{axis_name}] [直線]", yaxis=yaxis_id)
                    # ③ 曲線
                    if show_curve:
                        shape_type = determine_shape(df, x_axis, y_axis)
                        fig.add_scatter(x=df[x_axis], y=df[y_axis], mode="lines", line=dict(shape=shape_type, color=assigned_color), name=f"{y_axis} [{axis_name}] [各点結び]", yaxis=axis_id)

        # グラフの右側に軸が並ぶため、グラフ本体の表示幅を調整
        layout_kwargs["margin"] = dict(r=60 * num_custom_axes)
        
        fig.update_layout(**layout_kwargs)
        st.plotly_chart(fig, use_container_width=True)

        # -----------------------------------------------------------------------------
        # 4. ファイル保存
        # -----------------------------------------------------------------------------
        st.header("4. データの保存")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 入力データをCSVで保存", data=csv, file_name="graph_data.csv", mime="text/csv")
