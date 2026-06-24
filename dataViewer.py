import os
import json
import pandas as pd
import plotly.graph_objects as go
import webview
import sys 
import base64

COLOR_MAP = {
    # --- Machine Activities ---
    "仕掛り | 終わり": "#1E88E5",  # Vivid Blue
    "測定":           "#00ACC1",  # Deep Cyan/Teal
    "箱替え":         "#8E24AA",  # Purple
    "材替え":         "#3949AB",  # Indigo
    "段取り":         "#00897B",  # Dark Teal
    "運搬":           "#5E35B1",  # Deep Purple
    "金型調整":       "#546E7A",  # Slate Blue Gray
    "機械故障":       "#E53935",  # Deep Alert Red
    "設備復旧":       "#FDD835",  # Bright Sun Yellow
    "スクラップ":     "#757575",  # Neutral Gray
    # --- Miscellaneous Activities ---
    "4S":             "#7CB342",  # Light Apple Green
    "朝礼":           "#FFB300",  # Amber / Warning Yellow
    "打ち合わせ":     "#FB8C00",  # Orange
    "QC":             "#D81B60",  # Magenta/Pink
    "休憩":           "#FDD835",  # Bright Sun Yellow
    "教育":           "#5E35B1",  # Deep Purple
    "その他":         "#757575",  # Neutral Gray
    "手待ち":         "#FF1200",  # RED
}

GROUP_HEADER_H = 28
ACTIVITY_ROW_H = 26
GROUP_GAP      = 6


# ── Dynamic Path Resolvers (Ensures execution safety anywhere) ────
def get_asset_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_external_data_path():
    """ Resolves external data folder relative to main script or standalone .exe root """
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "data")


class Api:
    def request_chart_render(self, target_date, operator_name):
        data_dir = get_external_data_path()
        filename = f"{target_date}_{operator_name}.csv"
        data_file_path = os.path.join(data_dir, filename)

        if not os.path.exists(data_file_path):
            return f"<h3 style='color:red;padding:20px;'>エラー: ファイル '{filename}' が見つかりませんでした。</h3>"

        try:
            meta_df = pd.read_csv(data_file_path, nrows=2, header=None, encoding="shift_jis", usecols=[0, 1])
            log_date = str(meta_df.iloc[0, 1]).split(" ")[0].replace("/", "-").strip()
            csv_operator = str(meta_df.iloc[1, 1]).strip()

            df = pd.read_csv(data_file_path, skiprows=3, encoding="shift_jis")
            df.columns = df.columns.str.strip()
            df['start_dt'] = pd.to_datetime(log_date + " " + df['開始時刻'].astype(str))
            df['end_dt']   = pd.to_datetime(log_date + " " + df['終了時刻'].astype(str))

            equipment_order = list(dict.fromkeys(df['設備'].tolist()))
            tree = {}
            for _, row in df.iterrows():
                equip = row['設備']
                act   = row['内容']
                if equip not in tree:
                    tree[equip] = []
                if act not in tree[equip]:
                    tree[equip].append(act)

            y_index    = {}
            group_info = []
            counter    = 0
            for equip in reversed(equipment_order):
                acts    = tree[equip]
                g_start = counter
                for act in reversed(acts):
                    y_index[(equip, act)] = counter
                    counter += 1
                g_end = counter - 1
                group_info.append({"equip": equip, "y_start": g_start, "y_end": g_end})
                counter += 1

            total_rows = counter
            shapes     = []
            hover_x    = []
            hover_y    = []
            hover_text = []

            for _, row in df.iterrows():
                equip = row['設備']
                act   = row['内容']
                color = COLOR_MAP.get(act, "#B0BEC5")
                yi    = y_index[(equip, act)]
                x0    = row['start_dt'].isoformat()
                x1    = row['end_dt'].isoformat()
                dur_s = int((row['end_dt'] - row['start_dt']).total_seconds())

                shapes.append(dict(
                    type="rect", xref="x", yref="y",
                    x0=x0, x1=x1,
                    y0=yi - 0.38, y1=yi + 0.38,
                    fillcolor=color, line=dict(width=0), opacity=0.92
                ))
                cx = (row['start_dt'] + (row['end_dt'] - row['start_dt']) / 2).isoformat()
                hover_x.append(cx)
                hover_y.append(yi)
                hover_text.append(
                    f"<b>{equip}</b><br>作業: {act}<br>"
                    f"開始: {row['開始時刻']}<br>終了: {row['終了時刻']}<br>時間: {dur_s}秒"
                )

            for g in group_info:
                sep_y = g["y_start"] - 0.5
                shapes.append(dict(
                    type="line", xref="paper", yref="y",
                    x0=0, x1=1, y0=sep_y, y1=sep_y,
                    line=dict(color="#aaaaaa", width=1, dash="dot")
                ))
                shapes.append(dict(
                    type="rect", xref="paper", yref="y",
                    x0=0, x1=1,
                    y0=g["y_end"] + 0.52, y1=g["y_end"] + 0.98,
                    fillcolor="#dce8f5", opacity=0.6, line=dict(width=0), layer="below"
                ))

            tick_vals  = []
            tick_texts = []
            for g in group_info:
                equip = g["equip"]
                acts  = tree[equip]
                tick_vals.append(g["y_end"] + 0.75)
                tick_texts.append(f"<b>{equip}</b>")
                for act in acts:
                    yi = y_index[(equip, act)]
                    tick_vals.append(yi)
                    tick_texts.append(f"\u3000{act}")

            x_min_pad = (df['start_dt'].min() - pd.Timedelta(minutes=2)).isoformat()
            x_max_pad = (df['end_dt'].max()   + pd.Timedelta(minutes=2)).isoformat()

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hover_x, y=hover_y, mode="markers",
                marker=dict(size=0, opacity=0),
                hovertemplate="%{text}<extra></extra>",
                text=hover_text, showlegend=False
            ))

            seen_acts = set()
            for _, row in df.iterrows():
                act = row['内容']
                if act not in seen_acts:
                    seen_acts.add(act)
                    fig.add_trace(go.Scatter(
                        x=[None], y=[None], mode="markers",
                        marker=dict(size=12, color=COLOR_MAP.get(act, "#B0BEC5"), symbol="square"),
                        name=act, showlegend=True
                    ))

            chart_h = max(500, total_rows * 24 + 80)
            fig.update_layout(
                title=dict(
                    text=f"設備・作業別 タイムラインチャート<br><sup>日付: {log_date} | 作業者: {csv_operator}</sup>",
                    font=dict(size=14)
                ),
                shapes=shapes,
                xaxis=dict(
                    range=[x_min_pad, x_max_pad],
                    tickformat="%H:%M", showgrid=True, gridcolor="#e8e8e8",
                    title="時間（タイムライン）", type="date"
                ),
                yaxis=dict(
                    tickvals=tick_vals, ticktext=tick_texts,
                    tickfont=dict(size=11, family="Meiryo, Yu Gothic, sans-serif"),
                    showgrid=False, range=[-0.6, total_rows - 0.2],
                    fixedrange=True, title="設備 / 作業内容"
                ),
                legend=dict(title="作業内容", x=1.01, y=1, xanchor="left"),
                margin=dict(l=10, r=150, t=70, b=50),
                plot_bgcolor="#f9f9f9", paper_bgcolor="#ffffff",
                height=chart_h,
                hoverlabel=dict(bgcolor="white", font_size=12, font_family="Meiryo, sans-serif")
            )
            return fig.to_html(include_plotlyjs='cdn', full_html=False)

        except Exception as e:
            import traceback
            return f"<h3 style='color:red;padding:20px;'>エラーが発生しました:<br>{str(e)}<br><pre>{traceback.format_exc()}</pre></h3>"

    def get_csv_list(self):
        """Scan data/ folder, return JSON list of {date, operator}."""
        data_dir = get_external_data_path()
        results  = []
        if not os.path.exists(data_dir):
            return json.dumps([])
        for fname in sorted(os.listdir(data_dir)):
            if fname.endswith(".csv"):
                parts = fname[:-4].split("_", 1)
                if len(parts) == 2:
                    results.append({"date": parts[0], "operator": parts[1]})
        return json.dumps(results, ensure_ascii=False)

    def get_summary_data(self, target_date, operator_name):
        """Return JSON summary: total seconds per activity type."""
        data_dir       = get_external_data_path()
        filename       = f"{target_date}_{operator_name}.csv"
        data_file_path = os.path.join(data_dir, filename)
        if not os.path.exists(data_file_path):
            return json.dumps({"error": f"ファイル '{filename}' が見つかりません"})
        try:
            meta_df = pd.read_csv(data_file_path, nrows=2, header=None, encoding="shift_jis", usecols=[0, 1])
            log_date     = str(meta_df.iloc[0, 1]).split(" ")[0].replace("/", "-").strip()
            csv_operator = str(meta_df.iloc[1, 1]).strip()
            df = pd.read_csv(data_file_path, skiprows=3, encoding="shift_jis")
            df.columns       = df.columns.str.strip()
            df['start_dt']   = pd.to_datetime(log_date + " " + df['開始時刻'].astype(str))
            df['end_dt']     = pd.to_datetime(log_date + " " + df['終了時刻'].astype(str))
            df['duration_s'] = (df['end_dt'] - df['start_dt']).dt.total_seconds().astype(int)
            by_act = (df.groupby('内容')['duration_s'].sum()
                        .reset_index()
                        .rename(columns={'内容': 'name', 'duration_s': 'seconds'})
                        .sort_values('seconds', ascending=False))
            return json.dumps({
                "date": log_date, "operator": csv_operator,
                "by_activity": by_act.to_dict(orient='records'),
                "total_seconds": int(df['duration_s'].sum())
            }, ensure_ascii=False)
        except Exception as e:
            import traceback
            return json.dumps({"error": str(e) + "\n" + traceback.format_exc()})

    def get_color_map(self):
        """Expose the Python COLOR_MAP directly to the JavaScript frontend"""
        return json.dumps(COLOR_MAP, ensure_ascii=False)


# Target the ui folder correctly whether running as raw script or .exe
UI_DIR = get_asset_path("UI")

try:
    with open(os.path.join(UI_DIR, "index.html"), "r", encoding="utf-8") as f:
        html_content = f.read()
    with open(os.path.join(UI_DIR, "style.css"), "r", encoding="utf-8") as f:
        css_content = f.read()
    with open(os.path.join(UI_DIR, "main.js"), "r", encoding="utf-8") as f:
        js_content = f.read()

    # Safely compile the isolated assets into a single delivery package
    UI_HTML = html_content.replace(
        "</head>", f"<style>{css_content}</style></head>"
    ).replace(
        "</body>", f"<script>{js_content}</script></body>"
    )

except FileNotFoundError as e:
    UI_HTML = f"<h3 style='color:red;padding:20px;'>Asset Loading Error: Missing directory or configuration file.<br>{e}</h3>"


# ── Active Download Event Interception Handler ─────────────────────
def on_download_triggered(window):
    """Intercepts asset downloads inside WebView2 frames and handles them"""
    try:
        # Evaluate JS to grab the last download or handle via window property if needed.
        # However, to avoid intercept crashes, we can safely log it first:
        print("Download action detected from Plotly toolbar.")
    except Exception as e:
        print(f"Download tracking log error: {e}")


if __name__ == "__main__":
    api = Api()
    window = webview.create_window(
        "作業日報管理システム (Work Report Dashboard)",
        html=UI_HTML,
        js_api=api,
        width=1200,
        height=850,
        maximized=True,
    )
    # Start app with active download routing hook attached
    webview.start(on_download_triggered, window)