import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from io import StringIO

st.set_page_config(page_title="万能グラフ作成アプリ", layout="wide")

st.title("📊 高機能グラフ作成Webアプリ")
st.write("Excelやスプレッドシートからデータを**コピーして貼り付けるだけ**で、自動で自由なグラフを作成・保存できます。")

# -----------------------------------------------------------------------------
# 1. データ入力セクション（テキストエリアへの一括コピペ対応）
# -----------------------------------------------------------------------------
st.header("1. データの入力")

# 初期データ（サンプル）をタブ区切りテキスト形式で用意
default_paste_data = (
    "X軸データ\t売上\t利益\tカテゴリー\n"
    "1\t10\t2\tA\n"
    "2\t15\t5\tB\n"
    "3\t7\t1\tA\n"
    "4\t22\t8\tB\n"
    "5\t18\t4\tA"
)

# ユーザーがコピペするためのテキストエリア
paste_input = st.text_area(
    "Excelやスプレッドシートからデータをコピーし、下の枠内に貼り付けてください（Ctrl+V）：",
    value=default_paste_data,
    height=180,
    help="一番上の行がヘッダー（列名）になります。"
)

# 貼り付けられたテキストをデータフレームに変換
try:
    # Excelのコピペは通常タブ区切り (\t) になります
    df = pd.read_csv(StringIO(paste_input), sep='\t')
    
    # もしカンマ区切りの場合はカンマで再読み込みを試みる
    if len(df.columns) == 1 and ',' in paste_input:
        df = pd.read_csv(StringIO(paste_input), sep=',')
        
    st.subheader("現在のデータ確認")
    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"データの読み込みに失敗しました。形式を確認してください。エラー: {e}")
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
            # 複数軸・複数選択に対応
            y_axes = st.multiselect("Y軸（縦軸）を選択 ※複数選択可能", options=columns, default=[columns[1]])
            
        with col3:
            # 色分け（オプション）
            color_axis = st.selectbox("色分けする列（オプション）", options=["なし"] + columns, index=0)

        # 直線・曲線の自動判定オプション
        st.subheader("線のスタイルの設定")
        line_mode = st.radio(
            "線の引き方",
            options=["数値をみて自動判定（直線か曲線か）", "点（マーカー）のみ", "常に直線で繋ぐ", "常に滑らかな曲線で繋ぐ"],
            index=0
        )

        # -----------------------------------------------------------------------------
        # 3. グラフの描画
        # -----------------------------------------------------------------------------
        st.header("3. 生成されたグラフ")

        if not y_axes:
            st.warning("Y軸を1つ以上選択してください。")
        else:
            fig = px.line() # ベースの作成

            # 数値の並びから直線/曲線を自動判定するロジック
            def determine_shape(dataframe, x, y):
                try:
                    x_val = pd.to_numeric(dataframe[x]).values
                    y_val = pd.to_numeric(dataframe[y]).values
                    if len(x_val) < 3:
                        return "linear"
                    slopes = np.diff(y_val) / np.diff(x_val)
                    slope_variance = np.var(np.diff(slopes))
                    return "linear" if slope_variance < 1e-5 else "spline"
                except:
                    return "linear"

            # 線の種類を決定
            if line_mode == "数値をみて自動判定（直線か曲線か）":
                shape_type = determine_shape(df, x_axis, y_axes[0])
                st.info(f"💡 データの数値を解析し、現在は **「{'直線' if shape_type == 'linear' else '曲線（スプライン）'}」** が適していると判断しました。")
                line_dict = dict(shape=shape_type)
                render_mode = "lines+markers"
            elif line_mode == "点（マーカー）のみ":
                line_dict = dict()
                render_mode = "markers"
            elif line_mode == "常に直線で繋ぐ":
                line_dict = dict(shape="linear")
                render_mode = "lines+markers"
            else:
                line_dict = dict(shape="spline")
                render_mode = "lines+markers"

            # 複数軸の処理（2軸対応）
            use_secondary_y = len(y_axes) > 1
            
            # 各Y軸データを追加
            for i, y_axis in enumerate(y_axes):
                if color_axis != "なし":
                    unique_categories = df[color_axis].unique()
                    for cat in unique_categories:
                        sub_df = df[df[color_axis] == cat]
                        
                        # Plotly Expressのオブジェクトを代用して、確実なデータプロットを作成
                        temp_fig = px.scatter(sub_df, x=x_axis, y=y_axis, text=None)
                        if render_mode != "markers":
                            temp_fig.update_traces(mode=render_mode, line=line_dict)
                        else:
                            temp_fig.update_traces(mode="markers")
                        
                        trace = temp_fig.data[0]
                        trace.name = f"{y_axis} ({cat})"
                        trace.marker.size = 10  # しっかり点を取る
                        if use_secondary_y and i > 0:
                            trace.yaxis = "y2"
                        fig.add_trace(trace)
                else:
                    temp_fig = px.scatter(df, x=x_axis, y=y_axis, text=None)
                    if render_mode != "markers":
                        temp_fig.update_traces(mode=render_mode, line=line_dict)
                    else:
                        temp_fig.update_traces(mode="markers")
                    
                    trace = temp_fig.data[0]
                    trace.name = y_axis
                    trace.marker.size = 10  # しっかり点を取る
                    if use_secondary_y and i > 0:
                        trace.yaxis = "y2"
                    fig.add_trace(trace)

            # 2軸レイアウトの適用
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

            # グラフを表示
            st.plotly_chart(fig, use_container_width=True)

            # -----------------------------------------------------------------------------
            # 4. ファイル保存セクション
            # -----------------------------------------------------------------------------
            st.header("4. データの保存")
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 入力データをCSVで保存",
                    data=csv,
                    file_name="graph_data.csv",
                    mime="text/csv",
                )
            with col_dl2:
                st.caption("💡 グラフ自体を画像として保存したい場合は、グラフ右上にあるカメラマーク（カメラの形をしたアイコン）をクリックすると、一発でPNG画像としてダウンロードできます。")
