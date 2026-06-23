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

// ── Home: Populate Dropdowns & Render Directories ─────────────
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

function buildOperatorDirectory() {
  const counts = {};
  allCsvList.forEach(item => {
    counts[item.operator] = (counts[item.operator] || 0) + 1;
  });

  const uniqueOperators = Object.keys(counts).sort();
  document.getElementById('op-count').textContent = '総数: ' + uniqueOperators.length + '名';

  renderDirectoryHTML(uniqueOperators, counts);
}

function renderDirectoryHTML(operators, counts) {
  const listEl = document.getElementById('opDirectoryList');
  if (operators.length === 0) {
    listEl.innerHTML = '<div style="padding:16px; color:#aaa; text-align:center; font-size:13px;">該当する作業者がいません</div>';
    return;
  }

  listEl.innerHTML = operators.map(op => {
    return '<div class="op-item" onclick="selectOperatorFromDirectory(\'' + op + '\')">' +
             '<span>👤 ' + op + '</span>' +
             '<span class="op-badge">' + counts[op] + ' 日分</span>' +
           '</div>';
  }).join('');
}

function filterOperatorDirectory() {
  const query = document.getElementById('opSearchInput').value.toLowerCase().trim();
  const counts = {};
  allCsvList.forEach(item => { counts[item.operator] = (counts[item.operator] || 0) + 1; });
  
  const filtered = Object.keys(counts).sort().filter(op => op.toLowerCase().includes(query));
  renderDirectoryHTML(filtered, counts);
}

function selectOperatorFromDirectory(operatorName) {
  const opLogs = allCsvList.filter(r => r.operator === operatorName);
  if (opLogs.length > 0) {
    const targetedLog = opLogs[opLogs.length - 1];
    document.getElementById('dateInput').value = targetedLog.date;
    populateOps(targetedLog.date);
    document.getElementById('opSelect').value = operatorName;
  }
}

window.addEventListener('pywebviewready', function () {
  const dateInput = document.getElementById('dateInput');
  
  dateInput.addEventListener('change', function () {
    populateOps(this.value);
  });

  pywebview.api.get_csv_list().then(function (raw) {
    allCsvList = JSON.parse(raw);
    buildOperatorDirectory();

    if (allCsvList.length > 0) {
      dateInput.value = allCsvList[0].date;
      populateOps(allCsvList[0].date);
      document.getElementById('opSelect').value = allCsvList[0].operator;
    } else {
      const today = new Date().toISOString().slice(0, 10);
      dateInput.value = today;
      populateOps(today);
    }
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

    document.getElementById('sum-title').textContent = '作業サマリー — ' + data.operator;
    document.getElementById('sum-sub').textContent = '日付: ' + data.date + ' ／ 総作業時間: ' + fmtSec(data.total_seconds);

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

    const tbody = document.getElementById('sum-tbody');
    acts.forEach(function (a) {
      const pct  = (a.seconds / data.total_seconds * 100).toFixed(1);
      const idle = (a.name === '手待ち');
      const dot  = '<span class="color-dot" style="background:' + (COLOR_MAP[a.name] || DEFAULT_CLR) + '"></span>';
      const tr   = document.createElement('tr');
      if (idle) tr.className = 'row-idle';
      tr.innerHTML = '<td>' + dot + a.name + '</td><td>' + fmtSec(a.seconds) + '</td><td>' + pct + '%</td>';
      tbody.appendChild(tr);
    });
    const tot = document.createElement('tr');
    tot.className = 'row-total';
    tot.innerHTML = '<td><b>合計</b></td><td><b>' + fmtSec(data.total_seconds) + '</b></td><td><b>100%</b></td>';
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