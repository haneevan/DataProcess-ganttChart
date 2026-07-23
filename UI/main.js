// ── State ──────────────────────────────────────────────────────
  let screen       = 'home';
  let selDate      = '';
  let selOperator  = '';
  let allCsvList   = [];
  let COLOR_MAP    = {};
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
      crumb.textContent = 'ホーム > まとめ';
    } else if (id === 'settings') {
      back.disabled = false; fwd.disabled = true;
      crumb.textContent = 'ホーム > 設定';
    }
  }

  function goBack() {
    if (screen === 'gantt' || screen === 'settings' || screen === 'summary') showScreen('home');
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

  function populateSummaryOperators() {
    const uniqueOperators = [...new Set(allCsvList.map(item => item.operator))].sort();
    const sumSel = document.getElementById('summaryOpSelect');
    if (!sumSel) return;

    sumSel.innerHTML = uniqueOperators.map(op => 
      '<option value="' + op + '"' + (op === selOperator ? ' selected' : '') + '>' + op + '</option>'
    ).join('');
  }

  function buildOperatorDirectory() {
    const counts = {};
    allCsvList.forEach(item => {
      counts[item.operator] = (counts[item.operator] || 0) + 1;
    });

    const uniqueOperators = Object.keys(counts).sort();
    const countEl = document.getElementById('op-count');
    if (countEl) countEl.textContent = '総数: ' + uniqueOperators.length + '名';

    renderDirectoryHTML(uniqueOperators, counts);
    populateSummaryOperators();
  }

  function groupDates(dateStrings) {
    if (!dateStrings || dateStrings.length === 0) return '';
    const uniqueDates = [...new Set(dateStrings)].sort();
    const dates = uniqueDates.map(d => {
      const parts = d.split('-');
      return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
    }).sort((a, b) => a - b);
    
    const groups = [];
    let currentGroup = [dates[0]];

    for (let i = 1; i < dates.length; i++) {
      const prev = dates[i - 1];
      const curr = dates[i];
      const diffTime = Math.abs(curr - prev);
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      if (diffDays === 1) {
        currentGroup.push(curr);
      } else if (diffDays > 0) {
        groups.push(currentGroup);
        currentGroup = [curr];
      }
    }
    groups.push(currentGroup);

    return groups.map(group => {
      const formatDay = (d) => (d.getMonth() + 1) + '/' + d.getDate();
      if (group.length === 1) return formatDay(group[0]);
      if (group.length === 2) return formatDay(group[0]) + ', ' + formatDay(group[1]);
      return formatDay(group[0]) + '～' + formatDay(group[group.length - 1]);
    }).join(', ');
  }

  function renderDirectoryHTML(operators, counts) {
    const listEl = document.getElementById('opDirectoryList');
    if (!listEl) return;
    if (operators.length === 0) {
      listEl.innerHTML = '<div style="padding:16px; color:#aaa; text-align:center; font-size:13px;">該当する作業者がいません</div>';
      return;
    }

    listEl.innerHTML = operators.map(op => {
      const opDates = allCsvList.filter(item => item.operator === op).map(item => item.date);
      const dateSummary = groupDates(opDates);

      return '<div class="op-item" onclick="selectOperatorFromDirectory(\'' + op + '\')" style="display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 12px 16px;">' +
              '<div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">' +
                '<span style="font-weight: bold; font-size: 14px; color: #333;">👤 ' + op + '</span>' +
                '<span class="op-badge">' + counts[op] + ' 日分</span>' +
              '</div>' +
              '<div style="font-size: 11.5px; color: #555; background: #e0f2f1; padding: 5px 10px; border-radius: 6px; width: 100%; box-sizing: border-box; margin-top: 4px; border-left: 4px solid #00ACC1; display: flex; align-items: center; gap: 6px;">' +
                '<span>📅</span>' +
                '<span style="font-weight: 500;">データ登録日: ' + dateSummary + '</span>' +
              '</div>' +
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

  // Detects the latest available date inside CSV files, defaulting to today if empty
  function getLatestAvailableDate() {
    if (!allCsvList || allCsvList.length === 0) {
      const today = new Date();
      const offset = today.getTimezoneOffset();
      return new Date(today.getTime() - (offset * 60 * 1000)).toISOString().slice(0, 10);
    }
    const dates = allCsvList.map(r => r.date).sort();
    return dates[dates.length - 1];
  }

  window.addEventListener('pywebviewready', function () {
    const dateInput = document.getElementById('dateInput');
    
    dateInput.addEventListener('change', function () {
      populateOps(this.value);
    });

    pywebview.api.get_color_map().then(function (mapRaw) {
      COLOR_MAP = JSON.parse(mapRaw);
      return pywebview.api.get_csv_list();
    }).then(function (raw) {
      allCsvList = JSON.parse(raw);
      buildOperatorDirectory();

      // Default date automatically selects the newest date present in data/ folder
      const latestDate = getLatestAvailableDate();
      dateInput.value = latestDate;
      populateOps(latestDate);

      const opsForLatest = allCsvList.filter(r => r.date === latestDate);
      if (opsForLatest.length > 0) {
        document.getElementById('opSelect').value = opsForLatest[0].operator;
      } else if (allCsvList.length > 0) {
        document.getElementById('opSelect').value = allCsvList[0].operator;
      }
    });
  });

  // ── Gantt Chart Renderer ───────────────────────────────────
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
      
      const scripts = Array.from(wrapper.getElementsByTagName('script'));
      scripts.forEach(function (oldScript) {
        const newScript = document.createElement('script');
        newScript.type = 'text/javascript';
        newScript.textContent = oldScript.textContent;
        document.body.appendChild(newScript);
        oldScript.remove();
      });
    });
  }

  // ── SUMMARY DASHBOARD RENDERER ──────────────────────────────
  function goSummary() {
    showScreen('summary');
    populateSummaryOperators();

    const sumSel = document.getElementById('summaryOpSelect');
    if (!sumSel.value && selOperator) {
      sumSel.value = selOperator;
    } else if (sumSel.options.length > 0) {
      sumSel.selectedIndex = 0;
    }

    const currentOp = sumSel.value;
    if (currentOp) {
      const opDates = allCsvList.filter(item => item.operator === currentOp).map(item => item.date).sort();
      if (opDates.length > 0) {
        document.getElementById('sumStartDate').value = opDates[0];
        document.getElementById('sumEndDate').value = opDates[opDates.length - 1];
      }
    }

    loadSummaryData();
  }

  function onSummaryOperatorChange() {
    const currentOp = document.getElementById('summaryOpSelect').value;
    if (currentOp) {
      const opDates = allCsvList.filter(item => item.operator === currentOp).map(item => item.date).sort();
      if (opDates.length > 0) {
        document.getElementById('sumStartDate').value = opDates[0];
        document.getElementById('sumEndDate').value = opDates[opDates.length - 1];
      }
    }
    loadSummaryData();
  }

  // Handler for the "↻最新" button: re-scans directory and sets view ONLY to the single newest date
  function refreshLatestSummaryData() {
    pywebview.api.get_csv_list().then(function (raw) {
      allCsvList = JSON.parse(raw);
      buildOperatorDirectory();
      
      const sumSel = document.getElementById('summaryOpSelect');
      const currentOp = sumSel.value || (allCsvList.length > 0 ? allCsvList[0].operator : '');
      
      if (currentOp) {
        sumSel.value = currentOp;
        const opDates = allCsvList.filter(item => item.operator === currentOp).map(item => item.date).sort();
        if (opDates.length > 0) {
          // Snap both start and end date to the single NEWEST available date
          const newestDate = opDates[opDates.length - 1];
          document.getElementById('sumStartDate').value = newestDate;
          document.getElementById('sumEndDate').value = newestDate;
        }
      }
      loadSummaryData();
    });
  }

  function loadSummaryData() {
    const operator = document.getElementById('summaryOpSelect').value;
    const start    = document.getElementById('sumStartDate').value;
    const end      = document.getElementById('sumEndDate').value;

    if (!operator) {
      alert('作業者を選択してください。');
      return;
    }

    const tbody = document.getElementById('sum-detail-tbody');
    tbody.innerHTML = '<tr><td colspan="6" style="padding:20px; text-align:center; color:#888;">⏳ データ読み込み中...</td></tr>';

    pywebview.api.get_summary_range_data(operator, start, end).then(function (raw) {
      const data = JSON.parse(raw);

      if (data.error) {
        tbody.innerHTML = '<tr><td colspan="6" style="padding:20px; text-align:center; color:#e53935;">' + data.error + '</td></tr>';
        document.getElementById('sum-barchart-container').innerHTML = '<div style="display:flex; justify-content:center; align-items:center; height:100%; color:#aaa;">データがありません</div>';
        return;
      }

      if (data.rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="padding:20px; text-align:center; color:#888;">データがありません。</td></tr>';
      } else {
        tbody.innerHTML = data.rows.map(r => {
          return '<tr>' +
                   '<td>' + r.date.replace(/-/g, '/') + '</td>' +
                   '<td>' + r.equipment + '</td>' +
                   '<td>' + r.content + '</td>' +
                   '<td>' + r.start_time + '</td>' +
                   '<td>' + r.end_time + '</td>' +
                   '<td>' + r.duration_min + '</td>' +
                 '</tr>';
        }).join('');
      }

      renderSummaryBarChart(data);
    });
  }

  function renderSummaryBarChart(data) {
    if (typeof Plotly === 'undefined') {
      setTimeout(() => renderSummaryBarChart(data), 200);
      return;
    }

    const dates = data.dates;
    const activities = data.unique_activities;
    const dailyMap = data.daily_activities;
    const colors = data.colors || {};

    const traces = activities.map(act => {
      const yValues = dates.map(d => (dailyMap[d] && dailyMap[d][act]) ? dailyMap[d][act] : 0);
      return {
        x: dates.map(d => d.replace(/-/g, '/')),
        y: yValues,
        name: act,
        type: 'bar',
        marker: { color: colors[act] || DEFAULT_CLR }
      };
    });

    const layout = {
      barmode: 'group',
      margin: { t: 30, b: 50, l: 50, r: 20 },
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      xaxis: { title: '日付', type: 'category', tickfont: { size: 11 } },
      yaxis: { title: '合計時間 (分)', showgrid: true, gridcolor: '#e0e0e0' },
      legend: { orientation: 'h', x: 0, y: 1.12, font: { size: 11 } },
      autosize: true
    };

    Plotly.newPlot('sum-barchart-container', traces, layout, { responsive: true, displayModeBar: false });
  }

  function exportSummaryCSV() {
    const operator = document.getElementById('summaryOpSelect').value;
    const start    = document.getElementById('sumStartDate').value;
    const end      = document.getElementById('sumEndDate').value;

    const rows = Array.from(document.querySelectorAll('#sum-detail-tbody tr'));
    if (rows.length === 0 || rows[0].cells.length < 6) {
      alert('出力するデータがありません。');
      return;
    }

    let csvContent = "日付,設備,内容,開始時刻,終了時刻,合計(分)\n";
    rows.forEach(tr => {
      const cols = Array.from(tr.cells).map(td => '"' + td.textContent.trim() + '"');
      csvContent += cols.join(',') + "\n";
    });

    const blob = new Blob([new Uint8Array([0xEF, 0xBB, 0xBF]), csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `Summary_${operator}_${start}_to_${end}.csv`;
    link.click();
  }

  // ── Settings View Panels ──────────────────────────────────────────
  function showSettings() {
    showScreen('settings');
    loadSettingsPanel();
  }

  function loadSettingsPanel() {
    pywebview.api.get_registered_activities().then(function(mapping) {
      const tbody = document.getElementById('activities-list-body');
      if (!tbody) return;
      tbody.innerHTML = ''; 
      
      for (const [activity, colorHex] of Object.entries(mapping)) {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: left;">${activity}</td>
          <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: center;">
            <input type="color" value="${colorHex}" 
                   onchange="saveColorChange('${activity}', this.value)" 
                   style="border: none; cursor: pointer; width:40px; height:24px;">
          </td>
          <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: center;">
            <button onclick="deleteActivityItem('${activity}')" 
                    style="background: none; border: none; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; padding: 4px 8px;" 
                    title="削除">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e53935" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                <line x1="10" y1="11" x2="10" y2="17"></line>
                <line x1="14" y1="11" x2="14" y2="17"></line>
              </svg>
            </button>
          </td>
        `;
        tbody.appendChild(row);
      }
    });
  }

  function saveColorChange(activityName, newHex) {
    pywebview.api.update_activity_color(activityName, newHex).then(function(response) {
      console.log("Color updated securely for: " + activityName);
      COLOR_MAP[activityName] = newHex; 
    });
  }

  function deleteActivityItem(activityName) {
    if (confirm(`「${activityName}」の設定を完全に削除しますか？`)) {
      pywebview.api.delete_activity(activityName).then(function(response) {
        if (response.status === "success") {
          console.log("Successfully removed: " + activityName);
          if (activityName in COLOR_MAP) {
            delete COLOR_MAP[activityName];
          }
          loadSettingsPanel();
        } else {
          alert("エラー: " + response.message);
        }
      }).catch(function(err) {
        console.error("Deletion communication error: ", err);
      });
    }
  }