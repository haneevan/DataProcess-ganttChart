import os
import pandas as pd
import plotly.express as px
import tkinter as tk
from tkinter import messagebox
import webview  # Modern browser window engine wrapper

COLOR_MAP = {
    "点検": "#1E88E5", "測定": "#00ACC1", "加工": "#43A047", "箱替え": "#8E24AA",
    "段取り": "#3949AB", "材替え": "#00897B", "クレーン": "#5E35B1", "終わり": "#546E7A",
    "朝礼": "#FFFFB3", "4S": "#7CB342", "打ち合わせ": "#FB8C00", "QC": "#D81B60",
    "残業": "#E53935", "選別": "#6D4C41", "休憩": "#FDD835", "その他": "#757575"
}

def load_and_render_chart():
    target_date = date_entry.get().strip()  # e.g., "2026-06-23"
    operator_name = operator_entry.get().strip()  # e.g., "クンチョロ"
    data_dir = "data"

    # Changed filename construction to include the dash format
    filename = f"{target_date}_{operator_name}.csv"  # e.g., "2026-06-23_クンチョロ.csv"
    data_file_path = os.path.join(data_dir, filename)

    if not os.path.exists(data_file_path):
        messagebox.showerror("Error", f"ファイル '{filename}' が見つかりませんでした。\nパス: {os.path.abspath(data_file_path)}")
        return

    try:
        # 1. Read metadata block
        meta_df = pd.read_csv(data_file_path, nrows=2, header=None, encoding="shift_jis")
        
        # Since your filename now uses dashes, we make sure log_date handles dashes cleanly
        log_date = str(meta_df.iloc[0, 1]).split(" ")[0].replace("/", "-").strip()
        csv_operator = str(meta_df.iloc[1, 1]).strip()

        # 2. Load timetable dataset
        df = pd.read_csv(data_file_path, skiprows=3, encoding="shift_jis")
        df.columns = df.columns.str.strip()

        df['start_dt'] = pd.to_datetime(log_date + " " + df['開始時刻'].astype(str))
        df['end_dt'] = pd.to_datetime(log_date + " " + df['終了時刻'].astype(str))
        df['y_axis_label'] = df['設備'] + " - " + df['内容']

        chart_title = f"設備・作業別 タイムラインチャート<br><sup>日付: {log_date} | 作業者: {csv_operator}</sup>"

        # 3. Create the Plotly timeline object
        fig = px.timeline(
            df, x_start="start_dt", x_end="end_dt", y="y_axis_label",
            color="内容", title=chart_title, hover_data=["内容"], color_discrete_map=COLOR_MAP
        )
        fig.update_yaxes(categoryorder="category descending", title_text="設備 / 作業内容", showgrid=True)
        fig.update_xaxes(title_text="時間（タイムライン）", tickformat="%H:%M:%S", showgrid=True, dtick=10000)
        fig.update_layout(margin=dict(l=20, r=20, t=60, b=20))

        # 4. Save as a temporary HTML file
        temp_html_path = "temp_chart.html"
        fig.write_html(temp_html_path, include_plotlyjs=True)

        # 5. Launch or refresh the browser frame windows cleanly
        active_window = webview.active_window()
        if active_window:
            active_window.load_url(os.path.abspath(temp_html_path))
        else:
            webview.create_window(
                title=f"Timeline Chart - {csv_operator}", 
                url=os.path.abspath(temp_html_path),
                width=1200,
                height=700
            )
            webview.start()

    except Exception as e:
        messagebox.showerror("Error", f"エラーが発生しました:\n{str(e)}")

# --- Setup Primary Tkinter Controller UI ---
root = tk.Tk()
root.title("作業日報管理システム (Controller)")
root.geometry("450x150")
root.resizable(False, False)

# Main control container panel block
control_panel = tk.Frame(root)
control_panel.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

# Date Field Components Layout
tk.Label(control_panel, text="日付 (YYYYMMDD):", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
date_entry = tk.Entry(control_panel, font=("Arial", 10), width=20)
date_entry.insert(0, "20260623")  
date_entry.grid(row=0, column=1, padx=10, pady=5)

# Operator Field Components Layout
tk.Label(control_panel, text="作業者名:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=5)
operator_entry = tk.Entry(control_panel, font=("Arial", 10), width=20)
operator_entry.insert(0, "クンチョロ")  
operator_entry.grid(row=1, column=1, padx=10, pady=5)

# Submit Trigger Action Setup
load_button = tk.Button(
    control_panel, text="チャートを表示 / 更新", 
    command=load_and_render_chart, 
    font=("Arial", 10, "bold"), bg="#1E88E5", fg="white", width=25
)
load_button.grid(row=2, column=0, columnspan=2, pady=15)

root.mainloop()