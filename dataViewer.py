import os
import pandas as pd
import plotly.express as px
import webview

COLOR_MAP = {
    "点検": "#1E88E5", "測定": "#00ACC1", "加工": "#43A047", "箱替え": "#8E24AA",
    "段取り": "#3949AB", "材替え": "#00897B", "クレーン": "#5E35B1", "終わり": "#546E7A",
    "朝礼": "#FFFFB3", "4S": "#7CB342", "打ち合わせ": "#FB8C00", "QC": "#D81B60",
    "残業": "#E53935", "選別": "#6D4C41", "休憩": "#FDD835", "その他": "#757575"
}

class Api:
    """Exposes Python logic directly to our window UI controls."""
    def request_chart_render(self, target_date, operator_name):
        data_dir = "data"
        filename = f"{target_date}_{operator_name}.csv"
        data_file_path = os.path.join(data_dir, filename)

        if not os.path.exists(data_file_path):
            return f"<h3 style='color:red; padding:20px;'>エラー: ファイル '{filename}' が見つかりませんでした。</h3>"

        try:
            # 1. Read metadata block
            meta_df = pd.read_csv(data_file_path, nrows=2, header=None, encoding="shift_jis")
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

            # Export graph snippet directly with CDN scripts attached cleanly
            return fig.to_html(include_plotlyjs='cdn', full_html=False)

        except Exception as e:
            return f"<h3 style='color:red; padding:20px;'>エラーが発生しました:<br>{str(e)}</h3>"

# --- Fixed UI Framework with Secure DOM Script Unpacking ---
UI_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { margin: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #f5f7fb; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        .control-deck { background: #eaeaea; padding: 12px 20px; display: flex; align-items: center; gap: 15px; border-bottom: 1px solid #ccc; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        label { font-size: 14px; font-weight: bold; color: #333; }
        input { padding: 6px 10px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px; width: 140px; }
        button { padding: 7px 16px; font-size: 14px; font-weight: bold; background-color: #1E88E5; color: white; border: none; border-radius: 4px; cursor: pointer; transition: background 0.2s; }
        button:hover { background-color: #1565C0; }
        #canvas-wrapper { flex: 1; width: 100%; height: 100%; overflow: auto; }
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
            
            pywebview.api.request_chart_render(dt, op).then(function(responseHtml) {
                const wrapper = document.getElementById('canvas-wrapper');
                
                // Set the HTML content safely
                wrapper.innerHTML = responseHtml;
                
                // FIX: Extract script blocks and inject them as verified DOM elements 
                // so the browser engine triggers the Plotly timeline canvas assembly sequence.
                const scripts = Array.from(wrapper.getElementsByTagName('script'));
                scripts.forEach(oldScript => {
                    const newScript = document.createElement('script');
                    newScript.type = 'text/javascript';
                    if (oldScript.src) {
                        newScript.src = oldScript.src;
                    } else {
                        newScript.textContent = oldScript.textContent;
                    }
                    document.body.appendChild(newScript);
                    oldScript.remove(); // Clear old tracking elements
                });
            });
        }
        
        window.addEventListener('pywebviewready', function() {
            updateChart();
        });
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