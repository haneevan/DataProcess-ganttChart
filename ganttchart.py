import os
import pandas as pd
import plotly.express as px

# Create the explicit mapping matching the Android hex codes
COLOR_MAP = {
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

def generate_gantt_chart(target_date: str, operator_name: str, data_dir: str = "data"):
    """
    Dynamically loads the CSV based on date and operator name,
    and displays the Plotly Gantt Chart.
    
    :param target_date: Format 'YYYYMMDD' (e.g., '20260623')
    :param operator_name: Name of the operator (e.g., 'クンチョロ')
    :param data_dir: The directory where the files are stored
    """
    # 1. Dynamically build the filename using your new format
    filename = f"{target_date}_{operator_name}.csv"
    data_file_path = os.path.join(data_dir, filename)

    # Check if the file actually exists before processing
    if not os.path.exists(data_file_path):
        print(f"Error: The report file '{filename}' was not found in directory '{data_dir}'.")
        return

    print(f"Processing report: {filename}...")

    # 2. Read metadata FIRST to grab the formatted Date and Operator Name
    meta_df = pd.read_csv(data_file_path, nrows=2, header=None, encoding="shift_jis")
    log_date = str(meta_df.iloc[0, 1]).split(" ")[0].replace("/", "-").strip() # Pulls "2026-06-23"
    csv_operator = str(meta_df.iloc[1, 1]).strip()                            # Pulls "クンチョロ"

    # 3. Load the main activity data table (skipping the top metadata header)
    df = pd.read_csv(data_file_path, skiprows=3, encoding="shift_jis")
    df.columns = df.columns.str.strip()

    # 4. Combine retrieved date string with timestamps to build Datetime structures
    df['start_dt'] = pd.to_datetime(log_date + " " + df['開始時刻'].astype(str))
    df['end_dt'] = pd.to_datetime(log_date + " " + df['終了時刻'].astype(str))

    # 5. Format row labels dynamically
    df['y_axis_label'] = df['設備'] + " - " + df['内容']

    # 6. Build dynamic subtitle details directly inside HTML break tags
    chart_title = f"設備・作業別 タイムラインチャート<br><sup>日付: {log_date} | 作業者: {csv_operator}</sup>"

    # 7. Drawing the Gantt Chart with color mapped to activity types
    fig = px.timeline(
        df, 
        x_start="start_dt", 
        x_end="end_dt", 
        y="y_axis_label",      
        color="内容",      
        title=chart_title,      
        hover_data=["内容"] ,
        color_discrete_map=COLOR_MAP
    )

    # 8. Adjust layouts and axis structures
    fig.update_yaxes(
        categoryorder="category descending", 
        title_text="設備 / 作業内容",
        showgrid=True
    )
    fig.update_xaxes(
        title_text="時間（タイムライン）",
        tickformat="%H:%M:%S",
        showgrid=True,
        dtick=10000 
    )

    # 9. Render in user's browser window
    fig.show()

# --- Example Usage ---
if __name__ == "__main__":
    # You can quickly test different inputs here by changing these variables.
    # Later, your GUI or command-line args will pass values directly into this function.
    test_date = "20260623"
    test_operator = "クンチョロ"
    
    generate_gantt_chart(target_date=test_date, operator_name=test_operator)