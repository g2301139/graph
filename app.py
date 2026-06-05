import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from io import StringIO

st.set_page_config(page_title="万能グラフ作成アプリ", layout="wide")

st.title("📊 高機能グラフ作成Webアプリ")
st.write("Excelやスプレッドシートからデータを**コピーして貼り付けるだけ**で、トレンド線や複数軸のグラフを自動作成できます。")

# -----------------------------------------------------------------------------
# 1. データ入力セクション
# -----------------------------------------------------------------------------
st.header("1. データの入力")

# 初期データ（ばらつきのあるサンプルデータ）
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
    height=180,
    help="一番上の行がヘッダー（列名）になります。"
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
        st.error("データを2列以上入力（貼り付け）してください。")
    else:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            x_axis = st.selectbox("X軸（横軸）を選択", options=columns, index=0)
        with col2:
            y_axes = st.multiselect("Y軸（縦軸）を選択 ※複数選択可能", options=columns, default=[columns[1]])
        with col3:
            color_axis = st.selectbox("色分けする列（オプション）", options=["なし"] + columns, index=0)

        # 線の引き方の選択肢をアップデート
        st.subheader("線のスタイルの設定")
        line_mode = st.radio(
            "線の引き方",
            options=[
                "全体の平均を通る一直線（回帰直線／トレンドライン）", 
                "数値をみて自動判定（各点を通る直線か曲線か）", 
                "点（マーカー）のみ"
            ],
            index=0
        )

        # -----------------------------------------------------------------------------
        # 3. グラフの描画
        # -----------------------------------------------------------------------------
        st.header("3. 生成されたグラフ")

        if not y_axes:
            st.warning("Y軸を1つ以上選択してください。")
        else:
            # 描画用のベースフィギュア
            fig = px.line()
            use_secondary_y = len(y_axes) > 1

            # 最小二乗法で「平均的な一直線」のデータを計算する関数
            def get_trendline_data(dataframe, x_col, y_col):
                try:
                    x_vals = pd.to_numeric(dataframe[x_col]).values
                    y_vals = pd.to_numeric(dataframe[y_col]).values
                    # 一次関数 (y = ax + b) の係数を計算
                    idx = np.isfinite(x_vals) & np.isfinite(y_vals)
                    a, b = np.polyfit(x_vals[idx], y_vals[idx], 1)
                    
                    # 直線を描くための端と端の点を返す
                    x_trend = np.array([min(x_vals), max(x_vals)])
                    y_trend = a * x_trend + b
                    return x_trend, y_trend
                except:
                    return None, None

            # 自動判定ロジック
            def determine_shape(dataframe, x, y):
                try:
                    x_val = pd.to_numeric(dataframe[x]).values
                    y_val = pd.to_numeric(dataframe[y]).values
                    if len(x_val) < 3: return "linear"
                    slopes = np.diff(y_val) / np.diff(x_val)
                    return "linear" if np.var(np.diff(slopes)) < 1e-5 else "spline"
                except:
                    return "linear"

            # 選択されたすべてのY軸をプロット
            for i, y_axis in enumerate(y_axes):
                yaxis_target = "y2" if (use_secondary_y and i > 0) else "y"

                if color_axis != "なし":
                    unique_categories = df[color_axis].unique()
                    for cat in unique_categories:
                        sub_df = df[df[color_axis] == cat]
                        
                        # 1. まず「実際の点（マーカー）」をしっかりプロット
                        fig.add_scatter(
                            x=sub_df[x_axis], y=sub_df[y_axis],
                            mode="markers",
                            marker=dict(size=10),
                            name=f"{y_axis} ({cat}) - 実測値",
                            yaxis=yaxis_target
                        )
                        
                        # 2. 設定に合わせて線を引く
                        if line_mode == "全体の平均を通る一直線（回帰直線／トレンドライン）":
                            x_t, y_t = get_trendline_data(sub_df, x_axis, y_axis)
                            if x_t is not None:
                                fig.add_scatter(x=x_t, y=y_t, mode="lines", name=f"{y_axis} ({cat}) - トレンド線", yaxis=yaxis_target)
                        elif line_mode == "数値をみて自動判定（各点を通る直線か曲線か）":
                            shape_type = determine_shape(sub_df, x_axis, y_axis)
                            fig.add_scatter(x=sub_df[x_axis], y=sub_df[y_axis], mode="lines", line=dict(shape=shape_type), name=f"{y_axis} ({cat}) - 軌跡", yaxis=yaxis_target)
                
                else:
                    # 色分けなしの場合
                    fig.add_scatter(
                        x=df[x_axis], y=df[y_axis],
                        mode="markers",
                        marker=dict(size=10),
                        name=f"{y_axis} - 実測値",
                        yaxis=yaxis_target
                    )
                    
                    if line_mode == "全体の平均を通る一直線（回帰直線／トレンドライン）":
                        x_t, y_t = get_trendline_data(df, x_axis, y_axis)
                        if x_t is not None:
                            fig.add_scatter(x=x_t, y=y_t, mode="lines", name=f"{y_axis} - トレンド線", yaxis=yaxis_target)
                    elif line_mode == "数値をみて自動判定（各点を通る直線か曲線か）":
                        shape_type = determine_shape(df, x_axis, y_axis)
                        fig.add_scatter(x=df[x_axis], y=df[y_axis], mode="lines", line=dict(shape=shape_type), name=f"{y_axis} - 軌跡", yaxis=yaxis_target)

            # レイアウト設定
            layout_kwargs = {
                "xaxis": dict(title=x_axis),
                "yaxis": dict(title=y_axes[0]),
                "hovermode": "closest"
            }
            if use_secondary_y:
                layout_kwargs["yaxis2"] = dict(
                    title=y_axes[1] if len(y_axes) > 1 else "第2軸",
                    overlaying="y",
                    side="right"
                )
            fig.update_layout(**layout_kwargs)
            st.plotly_chart(fig, use_container_width=True)

            # -----------------------------------------------------------------------------
            # 4. ファイル保存セクション
            # -----------------------------------------------------------------------------
            st.header("4. データの保存")
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 入力データをCSVで保存", data=csv, file_name="graph_data.csv", mime="text/csv")
