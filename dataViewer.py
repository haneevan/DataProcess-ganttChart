import os
import json
import pandas as pd
import plotly.graph_objects as go
import webview

COLOR_MAP = {
    "点検": "#1E88E5",
    "測定": "#00ACC1",
    "加工": "#43A047",
    "箱替え": "#8E24AA",
    "段取り": "#3949AB",
    "材替え": "#00897B",
    "クレーン": "#5E35B1",
    "終わり": "#546E7A",
    "手待ち": "#FF0000",
    "朝礼": "#FDD835",
    "4S": "#7CB342",
    "打ち合わせ": "#FB8C00",
    "QC": "#D81B60",
    "残業": "#E53935",
    "選別": "#6D4C41",
    "休憩": "#FFCA28",
    "その他": "#757575"
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
                color = COLOR_MAP.get(act, "#9E9E9E")
                yi    = y_index[(equip, act)]
                x0    = row['start_dt'].timestamp() * 1000
                x1    = row['end_dt'].timestamp()   * 1000
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
                # invisible hover point at bar center
                cx = (x0 + x1) / 2
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
            x_min = df['start_dt'].min().timestamp() * 1000
            x_max = df['end_dt'].max().timestamp()   * 1000
            pad   = (x_max - x_min) * 0.01

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
                        marker=dict(size=12, color=COLOR_MAP.get(act, "#9E9E9E"), symbol="square"),
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
                    range=[x_min - pad, x_max + pad],
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
        height=850
    )
    webview.start()