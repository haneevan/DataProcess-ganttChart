import os
import json
import pandas as pd
import plotly.graph_objects as go
import webview

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

# Height constants (px)
GROUP_HEADER_H = 28   # bold equipment header row
ACTIVITY_ROW_H = 26   # each activity sub-row
GROUP_GAP       = 6   # gap between equipment groups

class Api:
    def request_chart_render(self, target_date, operator_name):
        data_dir = "data"
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

            # ── Build tree structure ──────────────────────────────────────────
            # equipment_order: unique equipment in first-appearance order
            equipment_order = list(dict.fromkeys(df['設備'].tolist()))

            # For each equipment, collect unique activities in first-appearance order
            tree = {}  # { equip: [act1, act2, ...] }
            for _, row in df.iterrows():
                equip = row['設備']
                act   = row['内容']
                if equip not in tree:
                    tree[equip] = []
                if act not in tree[equip]:
                    tree[equip].append(act)

            # ── Assign Y numeric positions ────────────────────────────────────
            # We'll use a numeric Y axis. Each activity sub-row gets an integer
            # Y index (0 = bottom). We build a mapping: (equip, act) → y_index
            # and record where each equipment group starts/ends for header rendering.
            y_index = {}       # (equip, act) → int
            group_info = []    # { equip, y_start, y_end } (y_start = first activity index)
            counter = 0

            # We render top-down visually, so the LAST equipment gets lowest y_index numbers.
            # Plotly y-axis goes bottom-up, so we build reversed.
            for equip in reversed(equipment_order):
                acts = tree[equip]
                g_start = counter
                for act in reversed(acts):   # reversed so first activity is at top
                    y_index[(equip, act)] = counter
                    counter += 1
                g_end = counter - 1
                group_info.append({"equip": equip, "y_start": g_start, "y_end": g_end})
                counter += 1   # +1 gap between groups

            total_rows = counter

            # ── Build Plotly shapes (bars) + hover traces ─────────────────────
            shapes = []
            hover_x = []
            hover_y = []
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
                    type="rect",
                    xref="x", yref="y",
                    x0=x0, x1=x1,
                    y0=yi - 0.38, y1=yi + 0.38,
                    fillcolor=color,
                    line=dict(width=0),
                    opacity=0.92
                ))
                # invisible hover point at bar center (midpoint datetime)
                cx = (row['start_dt'] + (row['end_dt'] - row['start_dt']) / 2).isoformat()
                hover_x.append(cx)
                hover_y.append(yi)
                hover_text.append(
                    f"<b>{equip}</b><br>作業: {act}<br>"
                    f"開始: {row['開始時刻']}<br>終了: {row['終了時刻']}<br>時間: {dur_s}秒"
                )

            # Group separator lines (horizontal, between equipment blocks)
            for g in group_info:
                # line just below the group (between groups)
                sep_y = g["y_start"] - 0.5
                shapes.append(dict(
                    type="line", xref="paper", yref="y",
                    x0=0, x1=1, y0=sep_y, y1=sep_y,
                    line=dict(color="#aaaaaa", width=1, dash="dot")
                ))
                # shaded header band just above the top activity row
                header_y_center = g["y_end"] + 0.5
                shapes.append(dict(
                    type="rect", xref="paper", yref="y",
                    x0=0, x1=1,
                    y0=g["y_end"] + 0.52, y1=g["y_end"] + 0.98,
                    fillcolor="#dce8f5", opacity=0.6, line=dict(width=0), layer="below"
                ))

            # ── Build tick labels: group header + indented activities ─────────
            tick_vals = []
            tick_texts = []
            for g in group_info:
                equip = g["equip"]
                acts  = tree[equip]
                # Header tick at midpoint of header band
                tick_vals.append(g["y_end"] + 0.75)
                tick_texts.append(f"<b>{equip}</b>")
                # Activity ticks
                for act in acts:
                    yi = y_index[(equip, act)]
                    tick_vals.append(yi)
                    tick_texts.append(f"　{act}")   # leading full-width space = indent

            # X axis: epoch ms range
            x_min = df['start_dt'].min().isoformat()
            x_max = df['end_dt'].max().isoformat()
            # pad of 2 minutes on each side
            x_min_pad = (df['start_dt'].min() - pd.Timedelta(minutes=2)).isoformat()
            x_max_pad = (df['end_dt'].max()   + pd.Timedelta(minutes=2)).isoformat()

            fig = go.Figure()

            # Invisible scatter for hover
            fig.add_trace(go.Scatter(
                x=hover_x, y=hover_y,
                mode="markers",
                marker=dict(size=0, opacity=0),
                hovertemplate="%{text}<extra></extra>",
                text=hover_text,
                showlegend=False
            ))

            # Legend dummy traces (one per activity type present)
            seen_acts = set()
            for _, row in df.iterrows():
                act = row['内容']
                if act not in seen_acts:
                    seen_acts.add(act)
                    fig.add_trace(go.Scatter(
                        x=[None], y=[None],
                        mode="markers",
                        marker=dict(size=12, color=COLOR_MAP.get(act, "#B0BEC5"), symbol="square"),
                        name=act,
                        showlegend=True
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
                    tickformat="%H:%M",
                    showgrid=True, gridcolor="#e8e8e8",
                    title="時間（タイムライン）",
                    type="date"
                ),
                yaxis=dict(
                    tickvals=tick_vals,
                    ticktext=tick_texts,
                    tickfont=dict(size=11, family="Meiryo, Yu Gothic, sans-serif"),
                    showgrid=False,
                    range=[-0.6, total_rows - 0.2],
                    fixedrange=True,
                    title="設備 / 作業内容"
                ),
                legend=dict(title="作業内容", x=1.01, y=1, xanchor="left"),
                margin=dict(l=10, r=150, t=70, b=50),
                plot_bgcolor="#f9f9f9",
                paper_bgcolor="#ffffff",
                height=chart_h,
                hoverlabel=dict(bgcolor="white", font_size=12, font_family="Meiryo, sans-serif")
            )

            return fig.to_html(include_plotlyjs='cdn', full_html=False)

        except Exception as e:
            import traceback
            return f"<h3 style='color:red;padding:20px;'>エラーが発生しました:<br>{str(e)}<br><pre>{traceback.format_exc()}</pre></h3>"


UI_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { margin: 0; font-family: 'Segoe UI', 'Meiryo', Arial, sans-serif; background-color: #f5f7fb; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        .control-deck { background: #eaeaea; padding: 12px 20px; display: flex; align-items: center; gap: 15px; border-bottom: 1px solid #ccc; box-shadow: 0 2px 4px rgba(0,0,0,0.05); flex-shrink: 0; }
        label { font-size: 14px; font-weight: bold; color: #333; }
        input { padding: 6px 10px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px; width: 140px; }
        button { padding: 7px 16px; font-size: 14px; font-weight: bold; background-color: #1E88E5; color: white; border: none; border-radius: 4px; cursor: pointer; transition: background 0.2s; }
        button:hover { background-color: #1565C0; }
        #canvas-wrapper { flex: 1; width: 100%; overflow: auto; }
    </style>
</head>
<body>
    <div class="control-deck">
        <label>日付 (YYYY-MM-DD):</label>
        <input type="text" id="dateInput" value="2026-06-23">
        <label>作業者名:</label>
        <input type="text" id="opInput" value="クンチョロ">
        <button onclick="updateChart()">チャートを表示 / 更新</button>
    </div>
    <div id="canvas-wrapper">
        <div style="padding: 30px; color: #666;"><h3>「チャートを表示」ボタンを押してデータを読み込んでください。</h3></div>
    </div>
    <script>
        function updateChart() {
            const dt = document.getElementById('dateInput').value;
            const op = document.getElementById('opInput').value;
            const wrapper = document.getElementById('canvas-wrapper');
            wrapper.innerHTML = '<div style="padding:30px;color:#888;">読み込み中...</div>';
            pywebview.api.request_chart_render(dt, op).then(function(responseHtml) {
                wrapper.innerHTML = responseHtml;
                const scripts = Array.from(wrapper.getElementsByTagName('script'));
                scripts.forEach(oldScript => {
                    const newScript = document.createElement('script');
                    newScript.type = 'text/javascript';
                    if (oldScript.src) { newScript.src = oldScript.src; }
                    else { newScript.textContent = oldScript.textContent; }
                    document.body.appendChild(newScript);
                    oldScript.remove();
                });
            });
        }
        window.addEventListener('pywebviewready', function() { updateChart(); });
    </script>
</body>
</html>
"""

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
    webview.start()