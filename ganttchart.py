import pandas as pd
import plotly.express as px

data_file_path = "data/WorkReport_20260619 4.csv"

# Create the explicit mapping match matching the Android hex codes
color_map = {
    # Machine Activities
    "点検": "#1E88E5",
    "測定": "#00ACC1",
    "加工": "#43A047",
    "箱替え": "#8E24AA",
    "段取り": "#3949AB",
    "材替え": "#00897B",
    "クレーン": "#5E35B1",
    "終わり": "#546E7A",
    
    # Miscellaneous Activities
    "朝礼": "#FFFFB3",
    "4S": "#7CB342",
    "打ち合わせ": "#FB8C00",
    "QC": "#D81B60",
    "残業": "#E53935",
    "選別": "#6D4C41",
    "休憩": "#FDD835",
    "その他": "#757575"
}

# 1. Read metadata FIRST to grab the Date and Operator Name dynamically
# We read the first two rows before skipping them for the main chart data
meta_df = pd.read_csv(data_file_path, nrows=2, header=None, encoding="shift_jis")
log_date = str(meta_df.iloc[0, 1]).split(" ")[0].replace("/", "-").strip() # Pulls "2026-06-19"
operator_name = str(meta_df.iloc[1, 1]).strip()                            # Pulls "クンチョロ"

# 2. Load the main activity data table (skipping the top metadata header)
df = pd.read_csv(data_file_path, skiprows=3, encoding="shift_jis")
df.columns = df.columns.str.strip()

# 3. Combine retrieved date string with timestamps to build Datetime structures
df['start_dt'] = pd.to_datetime(log_date + " " + df['開始時刻'].astype(str))
df['end_dt'] = pd.to_datetime(log_date + " " + df['終了時刻'].astype(str))

# 4. Format row labels dynamically
df['y_axis_label'] = df['設備'] + " - " + df['内容']

# 5. Build dynamic subtitle details directly inside HTML break tags
chart_title = f"設備・作業別 タイムラインチャート<br><sup>日付: {log_date} | 作業者: {operator_name}</sup>"

# 6. Drawing the Gantt Chart with color mapped to activity types
fig = px.timeline(
    df, 
    x_start="start_dt", 
    x_end="end_dt", 
    y="y_axis_label",       
    color="内容",      
    title=chart_title,      # Injected dynamic metadata header strings here
    hover_data=["内容"] ,
    color_discrete_map=color_map
)

# 7. Adjust layouts and axis structures
fig.update_yaxes(
    categoryorder="category descending", 
    title_text="設備 / 作業内容",
    showgrid=True              # Ensures the horizontal grid lines are visible
)
fig.update_xaxes(
    title_text="時間（タイムライン）",
    tickformat="%H:%M:%S",
    showgrid=True,             # Ensures the vertical grid lines are visible
    dtick=10000                # Forces a grid line every 10 seconds (10,000 milliseconds)
)

# 8. Render in user's browser window
fig.show()
