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

GROUP_HEADER_H = 28
ACTIVITY_ROW_H = 26
GROUP_GAP      = 6


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
        data_dir = "data"
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
        data_dir       = "data"
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


UI_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 0;
    font-family: 'Segoe UI', 'Meiryo', Arial, sans-serif;
    background: #f0f4f8;
    height: 100vh; display: flex; flex-direction: column; overflow: hidden;
  }

  /* NAV BAR */
  .navbar {
    background: #1565C0; color: white;
    padding: 0 20px; height: 48px;
    display: flex; align-items: center; gap: 12px;
    flex-shrink: 0; box-shadow: 0 2px 6px rgba(0,0,0,0.3);
  }
  .navbar h1 { font-size: 15px; font-weight: 600; margin: 0; flex: 1; }
  .nav-btn {
    background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3);
    color: white; padding: 5px 14px; border-radius: 4px;
    font-size: 13px; cursor: pointer; transition: background 0.15s;
    white-space: nowrap;
  }
  .nav-btn:hover  { background: rgba(255,255,255,0.28); }
  .nav-btn:disabled { opacity: 0.3; cursor: default; pointer-events: none; }
  .breadcrumb { font-size: 12px; opacity: 0.65; white-space: nowrap; }

  /* SCREENS */
  .screen { flex: 1; overflow: auto; display: none; }
  .screen.active { display: flex; flex-direction: column; }

  /* HOME */
  .home-wrap { display: flex; align-items: center; justify-content: center; flex: 1; padding: 32px 16px; }
  .home-card {
    background: white; border-radius: 14px;
    box-shadow: 0 6px 28px rgba(0,0,0,0.12);
    padding: 44px 52px; width: 460px; max-width: 95vw;
  }
  .home-card h2 { margin: 0 0 32px; font-size: 20px; color: #1565C0; text-align: center; letter-spacing: 0.5px; }
  .field-group { margin-bottom: 22px; }
  .field-group label { display: block; font-size: 12px; font-weight: 700; color: #666; margin-bottom: 7px; text-transform: uppercase; letter-spacing: 0.5px; }
  .field-group input[type=date],
  .field-group select {
    width: 100%; padding: 10px 13px; font-size: 14px;
    border: 1.5px solid #d0d5dd; border-radius: 7px;
    background: white; color: #111;
    font-family: 'Segoe UI', 'Meiryo', sans-serif;
    transition: border-color 0.15s;
  }
  .field-group input[type=date]:focus,
  .field-group select:focus { outline: none; border-color: #1E88E5; box-shadow: 0 0 0 3px rgba(30,136,229,0.12); }
  .btn-primary {
    width: 100%; padding: 12px; font-size: 15px; font-weight: 700;
    background: #1E88E5; color: white; border: none; border-radius: 7px;
    cursor: pointer; margin-top: 6px; transition: background 0.2s, transform 0.1s;
    letter-spacing: 0.3px;
  }
  .btn-primary:hover  { background: #1565C0; }
  .btn-primary:active { transform: scale(0.98); }
  .home-hint { font-size: 12px; color: #aaa; text-align: center; margin-top: 16px; }

  /* GANTT */
  #gantt-wrapper { flex: 1; overflow: auto; }

  /* SUMMARY */
  .sum-wrap { padding: 28px 36px; }
  .sum-header { margin-bottom: 24px; }
  .sum-header h2 { margin: 0 0 5px; font-size: 19px; color: #1565C0; }
  .sum-header p  { margin: 0; font-size: 13px; color: #777; }
  .sum-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  @media (max-width: 700px) { .sum-grid { grid-template-columns: 1fr; } }
  .sum-panel {
    background: white; border-radius: 10px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08); padding: 22px;
  }
  .sum-panel h3 { margin: 0 0 16px; font-size: 13px; font-weight: 700; color: #555;
    border-bottom: 1px solid #eee; padding-bottom: 10px; text-transform: uppercase; letter-spacing: 0.4px; }
  #pie-container { width: 100%; height: 310px; }
  .act-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .act-table th { text-align: left; padding: 8px 10px; background: #f7f8fa;
    color: #555; font-weight: 700; border-bottom: 2px solid #e4e4e4; font-size: 12px; }
  .act-table td { padding: 8px 10px; border-bottom: 1px solid #f2f2f2; }
  .act-table tr:last-child td { border-bottom: none; }
  .color-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%;
    margin-right: 8px; vertical-align: middle; flex-shrink: 0; }
  .row-idle td { background: #fff5f5 !important; color: #c62828; font-weight: 700; }
  .row-total td { font-weight: 700; background: #f7f8fa !important;
    border-top: 2px solid #ddd !important; }
</style>
</head>
<body>

<!-- NAVBAR -->
<div class="navbar">
  <button class="nav-btn" id="btn-back" onclick="goBack()" disabled>← 戻る</button>
  <h1>作業日報管理システム</h1>
  <span class="breadcrumb" id="breadcrumb">ホーム</span>
  <button class="nav-btn" id="btn-fwd" onclick="goSummary()" disabled>サマリー →</button>
</div>

<!-- SCREEN: HOME -->
<div class="screen active" id="screen-home">
  <div class="home-wrap">
    <div class="home-card">
      <h2>📋 データ選択</h2>
      <div class="field-group">
        <label>日付</label>
        <input type="date" id="dateInput">
      </div>
      <div class="field-group">
        <label>作業者名</label>
        <select id="opSelect">
          <option value="">-- 読み込み中... --</option>
        </select>
      </div>
      <button class="btn-primary" onclick="showGantt()">ガントチャートを表示 →</button>
      <p class="home-hint">data/ フォルダ内の CSV ファイルから自動検出</p>
    </div>
  </div>
</div>

<!-- SCREEN: GANTT -->
<div class="screen" id="screen-gantt">
  <div id="gantt-wrapper">
    <div style="padding:40px;color:#999;font-size:15px;">⏳ 読み込み中...</div>
  </div>
</div>

<!-- SCREEN: SUMMARY -->
<div class="screen" id="screen-summary">
  <div class="sum-wrap">
    <div class="sum-header">
      <h2 id="sum-title">作業サマリー</h2>
      <p  id="sum-sub"></p>
    </div>
    <div class="sum-grid">
      <div class="sum-panel">
        <h3>作業別 時間内訳</h3>
        <div id="pie-container"></div>
      </div>
      <div class="sum-panel">
        <h3>合計時間テーブル</h3>
        <table class="act-table">
          <thead>
            <tr><th>作業内容</th><th>合計時間</th><th>割合</th></tr>
          </thead>
          <tbody id="sum-tbody"></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<script>
// ── State ──────────────────────────────────────────────────────
let screen       = 'home';
let selDate      = '';
let selOperator  = '';
let allCsvList   = [];

const COLOR_MAP = {
  "仕掛り | 終わり": "#1E88E5", "測定": "#00ACC1", "箱替え": "#8E24AA",
  "材替え": "#3949AB", "段取り": "#00897B", "運搬": "#5E35B1",
  "金型調整": "#546E7A", "機械故障": "#E53935", "設備復旧": "#FDD835",
  "スクラップ": "#757575", "4S": "#7CB342", "朝礼": "#FFB300",
  "打ち合わせ": "#FB8C00", "QC": "#D81B60", "休憩": "#FDD835",
  "教育": "#5E35B1", "その他": "#757575", "手待ち": "#FF1200"
};
const DEFAULT_CLR = "#B0BEC5";

// ── Navigation ──────────────────────────────────────────────────
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById('screen-' + id).classList.add('active');
  screen = id;
  const back  = document.getElementById('btn-back');
  const fwd   = document.getElementById('btn-fwd');
  const crumb = document.getElementById('breadcrumb');
  if (id === 'home') {
    back.disabled = true; fwd.disabled = true;
    crumb.textContent = 'ホーム';
  } else if (id === 'gantt') {
    back.disabled = false; fwd.disabled = false;
    crumb.textContent = 'ホーム > ガント（' + selDate + ' / ' + selOperator + '）';
  } else if (id === 'summary') {
    back.disabled = false; fwd.disabled = true;
    crumb.textContent = 'ホーム > ガント > サマリー';
  }
}

function goBack() {
  if (screen === 'gantt')   showScreen('home');
  if (screen === 'summary') showScreen('gantt');
}

// ── Home: populate operator list by date ───────────────────────
function populateOps(targetDate) {
  const forDate = allCsvList.filter(r => r.date === targetDate);
  const pool    = forDate.length ? forDate : allCsvList;
  const ops     = [...new Set(pool.map(r => r.operator))].sort();
  const sel     = document.getElementById('opSelect');
  if (ops.length === 0) {
    sel.innerHTML = '<option value="">-- データなし --</option>';
  } else {
    sel.innerHTML = ops.map(o => '<option value="' + o + '">' + o + '</option>').join('');
  }
}

window.addEventListener('pywebviewready', function () {
  // Default date = today
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById('dateInput').value = today;
  document.getElementById('dateInput').addEventListener('change', function () {
    populateOps(this.value);
  });
  pywebview.api.get_csv_list().then(function (raw) {
    allCsvList = JSON.parse(raw);
    populateOps(today);
  });
});

// ── Gantt ───────────────────────────────────────────────────────
function showGantt() {
  selDate     = document.getElementById('dateInput').value;
  selOperator = document.getElementById('opSelect').value;
  if (!selDate || !selOperator) {
    alert('日付と作業者名を選択してください。'); return;
  }
  const wrapper = document.getElementById('gantt-wrapper');
  wrapper.innerHTML = '<div style="padding:40px;color:#999;font-size:15px;">⏳ チャート生成中...</div>';
  showScreen('gantt');

  pywebview.api.request_chart_render(selDate, selOperator).then(function (html) {
    wrapper.innerHTML = html;
    Array.from(wrapper.getElementsByTagName('script')).forEach(function (old) {
      const s = document.createElement('script');
      s.type = 'text/javascript';
      if (old.src) s.src = old.src; else s.textContent = old.textContent;
      document.body.appendChild(s);
      old.remove();
    });
  });
}

// ── Summary ─────────────────────────────────────────────────────
function goSummary() {
  showScreen('summary');
  document.getElementById('pie-container').innerHTML =
    '<div style="padding:20px;color:#aaa;">読み込み中...</div>';
  document.getElementById('sum-tbody').innerHTML = '';

  pywebview.api.get_summary_data(selDate, selOperator).then(function (raw) {
    const data = JSON.parse(raw);
    if (data.error) {
      document.getElementById('pie-container').innerHTML =
        '<p style="color:red;padding:12px;">' + data.error + '</p>';
      return;
    }

    document.getElementById('sum-title').textContent =
      '作業サマリー — ' + data.operator;
    document.getElementById('sum-sub').textContent =
      '日付: ' + data.date + '　／　総作業時間: ' + fmtSec(data.total_seconds);

    // Pie chart
    const acts   = data.by_activity;
    const labels = acts.map(function (a) { return a.name; });
    const values = acts.map(function (a) { return a.seconds; });
    const colors = labels.map(function (l) { return COLOR_MAP[l] || DEFAULT_CLR; });

    function tryPie() {
      if (typeof Plotly === 'undefined') { setTimeout(tryPie, 250); return; }
      Plotly.newPlot('pie-container', [{
        type: 'pie', labels: labels, values: values,
        marker: { colors: colors },
        textinfo: 'label+percent',
        textfont: { size: 11, family: 'Meiryo, sans-serif' },
        hovertemplate: '<b>%{label}</b><br>%{customdata}<br>%{percent}<extra></extra>',
        customdata: values.map(fmtSec),
        hole: 0.38, sort: false
      }], {
        margin: { t: 10, b: 10, l: 10, r: 10 },
        showlegend: false, paper_bgcolor: 'white', height: 300
      }, { responsive: true, displayModeBar: false });
    }
    tryPie();

    // Table
    const tbody = document.getElementById('sum-tbody');
    acts.forEach(function (a) {
      const pct  = (a.seconds / data.total_seconds * 100).toFixed(1);
      const idle = (a.name === '手待ち');
      const dot  = '<span class="color-dot" style="background:' +
                   (COLOR_MAP[a.name] || DEFAULT_CLR) + '"></span>';
      const tr   = document.createElement('tr');
      if (idle) tr.className = 'row-idle';
      tr.innerHTML = '<td>' + dot + a.name + '</td><td>' +
                     fmtSec(a.seconds) + '</td><td>' + pct + '%</td>';
      tbody.appendChild(tr);
    });
    const tot = document.createElement('tr');
    tot.className = 'row-total';
    tot.innerHTML = '<td><b>合計</b></td><td><b>' + fmtSec(data.total_seconds) +
                    '</b></td><td><b>100%</b></td>';
    tbody.appendChild(tot);
  });
}

function fmtSec(s) {
  const h   = Math.floor(s / 3600);
  const m   = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return h + '時間' + String(m).padStart(2,'0') + '分' + String(sec).padStart(2,'0') + '秒';
  if (m > 0) return m + '分' + String(sec).padStart(2,'0') + '秒';
  return sec + '秒';
}
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