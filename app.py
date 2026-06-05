import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="万能グラフ作成アプリ", layout="wide")

st.title("📊 高機能グラフ作成Webアプリ")
st.write("Excelやスプレッドシートからデータを**コピペ**するか、直接手入力して自由なグラフを作成できます。")

# -----------------------------------------------------------------------------
# 1. データ入力セクション（コピペ・手入力対応）
# -----------------------------------------------------------------------------
st.header("1. データの入力")

# 初期データ（サンプル）
default_data = {
    "X軸データ": [1, 2, 3, 4, 5],
    "売上": [10, 15, 7, 22, 18],
    "利益": [2, 5, 1, 8, 4],
    "カテゴリー": ["A", "B", "A", "B", "A"]
}
df_default = pd.DataFrame(default_data)

# st.data_editor を使うことで、画面上での手入力・コピペ（Ctrl+V）が可能になります
edited_df = st.data_editor(
    df_default, 
    num_rows="dynamic", 
    use_container_width=True,
    help="セルを選択してExcel等からコピーしたデータを貼り付け（Ctrl+V）できます。行の追加も可能です。"
)

# -----------------------------------------------------------------------------
# 2. グラフの設定セクション
# -----------------------------------------------------------------------------
st.header("2. グラフの設定")

columns = edited_df.columns.tolist()

if len(columns) < 2:
    st.error("データを2列以上入力してください（例: X軸、Y軸、色分け用カテゴリなど）")
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
        fig = px.Figure()

        # 数値の並びから直線/曲線を自動判定するロジック
        def determine_shape(df, x, y):
            try:
                # 念のため数値型に変換して判定
                x_val = pd.to_numeric(df[x]).values
                y_val = pd.to_numeric(df[y]).values
                
                # 3点以上ない場合は直線扱い
                if len(x_val) < 3:
                    return "linear"
                
                # 傾きの変化を計算 (2階差分のようなもの)
                slopes = np.diff(y_val) / np.diff(x_val)
                slope_variance = np.var(np.diff(slopes))
                
                # 傾きの変化がほぼゼロ（誤差の範囲）なら直線、それ以外なら曲線
                if slope_variance < 1e-5:
                    return "linear"
                else:
                    return "spline" # 滑らかな曲線
            except:
                return "linear" # エラー時はデフォルトで直線

        # 線の種類を決定
        if line_mode == "数値をみて自動判定（直線か曲線か）":
            # 最初のY軸をベースに判定
            shape_type = determine_shape(edited_df, x_axis, y_axes[0])
            st.info(f"💡 データの数値を解析し、現在は **「{'直線' if shape_type == 'linear' else '曲線（スプライン）'}」** が適していると判断しました。")
            line_dict = dict(shape=shape_type)
            render_mode = "lines+markers"
        elif line_mode == "点（マーカー）のみ":
            line_dict = dict()
            render_mode = "markers"
        elif line_mode == "常に直線で繋ぐ":
            line_dict = dict(shape="linear")
            render_mode = "lines+markers"
        else: # 常に滑らかな曲線
            line_dict = dict(shape="spline")
            render_mode = "lines+markers"

        # Y軸が複数ある場合の第2軸設定
        use_secondary_y = len(y_axes) > 1
        
        # 選択されたすべてのY軸プロットをループ
        for i, y_axis in enumerate(y_axes):
            # 色分けが指定されている場合
            if color_axis != "なし":
                unique_categories = edited_df[color_axis].unique()
                for cat in unique_categories:
                    sub_df = edited_df[edited_df[color_axis] == cat]
                    fig.add_trace(px.Scatter(
                        x=sub_df[x_axis],
                        y=sub_df[y_axis],
                        mode=render_mode,
                        line=line_dict,
                        marker=dict(size=10, symbol="circle"), # しっかり点を取る
                        name=f"{y_axis} ({cat})",
                        yaxis="y2" if (use_secondary_y and i > 0) else "y"
                    ).data[0])
            else:
                # 色分けなしの場合
                fig.add_trace(px.Scatter(
                    x=edited_df[x_axis],
                    y=edited_df[y_axis],
                    mode=render_mode,
                    line=line_dict,
                    marker=dict(size=10, symbol="circle"), # しっかり点を取る
                    name=y_axis,
                    yaxis="y2" if (use_secondary_y and i > 0) else "y"
                ).data[0])

        # レイアウトの設定（2軸対応とデザイン調整）
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

        # グラフ表示
        st.plotly_chart(fig, use_container_width=True)

        # -----------------------------------------------------------------------------
        # 4. ファイル保存セクション
        # -----------------------------------------------------------------------------
        st.header("4. データの保存")
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            # CSVとしてダウンロード
            csv = edited_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 編集後のデータをCSVで保存",
                data=csv,
                file_name="graph_data.csv",
                mime="text/csv",
            )
        with col_dl2:
            st.caption("💡 グラフ自体を画像として保存したい場合は、グラフ右上にあるカメラマーク（Camera icon）をクリックするとPNG形式でダウンロードできます。")
