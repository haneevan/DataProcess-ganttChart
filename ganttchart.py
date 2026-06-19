import pandas as pd
import plotly.express as px

# 1. データの読み込み（文字コードをShift_JISに指定）
df = pd.read_csv("data/WorkReport_20260620 3.csv", skiprows=3, encoding="shift_jis")

# 空白文字などのブレを防ぐためカラム名をトリミング
df.columns = df.columns.str.strip()

# 2. 日付と時刻を結合してDatetime型に変換
# ※1枚目の画像にあった「2026/6/19」を基準にしています
date_str = "2026-06-19 "
df['start_dt'] = pd.to_datetime(date_str + df['start time'].astype(str))
df['end_dt'] = pd.to_datetime(date_str + df['end time'].astype(str))

# 3. 画像のような「設備 > 作業内容」の階層構造をY軸で表現するためのラベルを作成
# これにより、同じ設備の中で作業内容ごとに別々の行（段差）が自動で割り振られます
df['y_axis_label'] = df['設備'] + " - " + df['work type']

# 4. ガントチャート（タイムライン）の描画
fig = px.timeline(
    df, 
    x_start="start_dt", 
    x_end="end_dt", 
    y="y_axis_label",       # 設備と作業内容をセットにしたラベルを行に指定
    color="設備",           # 設備（PRP-42、PRP-40、その他）ごとにバーの色を分ける
    title="設備・作業別 タイムラインチャート",
    hover_data=["work type"] # マウスを当てたときに作業内容を表示
)

# 5. レイアウトの調整（見やすさを画像に近づける）
fig.update_yaxes(
    categoryorder="category descending", # 設備名で綺麗に並ぶようソート
    title_text="設備 / 作業内容"
)
fig.update_xaxes(
    title_text="時間（タイムライン）",
    tickformat="%H:%M:%S" # 軸の表記を「時:分:秒」にフォーマット
)

# 6. ブラウザでインタラクティブなチャートを表示
fig.show()
