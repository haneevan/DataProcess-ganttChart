// ── State ──────────────────────────────────────────────────────
  let screen       = 'home';
  let selDate      = '';
  let selOperator  = '';
  let allCsvList   = [];
  let COLOR_MAP    = {};
  const DEFAULT_CLR = "#B0BEC5";

  // Raw fetched summary dataset and filter selections
  let rawSummaryData = null;
  let activeEquipmentFilters = new Set();
  let activeContentFilters   = new Set();
  let currentFilterColumn    = '';
  let durationSortMode       = 'none'; // 'none' (default), 'desc' (max->min), 'asc' (min->max)

  // ── Navigation ──────────────────────────────────────────────────
  function showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById('screen-' + id).classList.add('active');
    screen = id;
    const back  = document.getElementById('btn-back');
    const fwd   = document.getElementById('btn-fwd');
    const edit  = document.getElementById('btn-edit-data');
    const crumb = document.getElementById('breadcrumb');
    
    if (id === 'home') {
      back.disabled = true; fwd.disabled = true;
      crumb.textContent = 'ホーム';
    } else if (id === 'gantt') {
      back.disabled = false; fwd.disabled = false;
      edit.style.display = 'inline-block';
      crumb.textContent = 'ホーム > ガント（' + selDate + ' / ' + selOperator + '）';
    } else if (id === 'summary') {
      back.disabled = false; fwd.disabled = true;
      edit.style.display = 'none';
      crumb.textContent = 'ホーム > ガント > まとめ';
    } else if (id === 'settings') {
      back.disabled = false; fwd.disabled = true;
      edit.style.display = 'none';
      crumb.textContent = 'ホーム > 設定';
    }
    if (id === 'home') edit.style.display = 'none';
  }

  function goBack() {
    if (screen === 'gantt' || screen === 'settings') showScreen('home');
    else if (screen === 'summary') showScreen('gantt');
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

    const sumSel    = document.getElementById('summaryOpSelect');
    const homeOp    = document.getElementById('opSelect').value;
    const homeDate  = document.getElementById('dateInput').value;

    if (homeOp) {
      sumSel.value = homeOp;
    } else if (sumSel.options.length > 0) {
      sumSel.selectedIndex = 0;
    }

    if (homeDate) {
      document.getElementById('sumStartDate').value = homeDate;
      document.getElementById('sumEndDate').value   = homeDate;
    } else {
      const currentOp = sumSel.value;
      if (currentOp) {
        const opDates = allCsvList.filter(item => item.operator === currentOp).map(item => item.date).sort();
        if (opDates.length > 0) {
          const newest = opDates[opDates.length - 1];
          document.getElementById('sumStartDate').value = newest;
          document.getElementById('sumEndDate').value   = newest;
        }
      }
    }

    loadSummaryData();
  }

  function onSummaryOperatorChange() {
    const currentOp = document.getElementById('summaryOpSelect').value;
    if (currentOp) {
      const opDates = allCsvList.filter(item => item.operator === currentOp).map(item => item.date).sort();
      if (opDates.length > 0) {
        const newestDate = opDates[opDates.length - 1];
        document.getElementById('sumStartDate').value = newestDate;
        document.getElementById('sumEndDate').value   = newestDate;
      }
    }
    loadSummaryData();
  }

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
          const newestDate = opDates[opDates.length - 1];
          document.getElementById('sumStartDate').value = newestDate;
          document.getElementById('sumEndDate').value   = newestDate;
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

    durationSortMode = 'none'; // Reset sort when loading new data
    updateSortButtonState();

    const tbody = document.getElementById('sum-detail-tbody');
    tbody.innerHTML = '<tr><td colspan="6" style="padding:20px; text-align:center; color:#888;">⏳ データ読み込み中...</td></tr>';

    pywebview.api.get_summary_range_data(operator, start, end).then(function (raw) {
      const data = JSON.parse(raw);

      if (data.error) {
        tbody.innerHTML = '<tr><td colspan="6" style="padding:20px; text-align:center; color:#e53935;">' + data.error + '</td></tr>';
        document.getElementById('sum-barchart-container').innerHTML = '<div style="display:flex; justify-content:center; align-items:center; height:100%; color:#aaa;">データがありません</div>';
        return;
      }

      rawSummaryData = data;

      activeEquipmentFilters = new Set(data.rows.map(r => r.equipment));
      activeContentFilters   = new Set(data.rows.map(r => r.content));

      updateFilterHeaderButtonsState();
      renderFilteredSummaryView();
    });
  }

  function updateFilterHeaderButtonsState() {
    if (!rawSummaryData) return;

    const allEquipments = new Set(rawSummaryData.rows.map(r => r.equipment));
    const allContents   = new Set(rawSummaryData.rows.map(r => r.content));

    const btnEquip = document.getElementById('btn-filter-equipment');
    const btnCont  = document.getElementById('btn-filter-content');

    if (btnEquip) {
      if (activeEquipmentFilters.size < allEquipments.size) {
        btnEquip.classList.add('active-filter');
      } else {
        btnEquip.classList.remove('active-filter');
      }
    }

    if (btnCont) {
      if (activeContentFilters.size < allContents.size) {
        btnCont.classList.add('active-filter');
      } else {
        btnCont.classList.remove('active-filter');
      }
    }
  }

  function cycleDurationSort() {
    if (durationSortMode === 'none') {
      durationSortMode = 'desc'; // Max to min
    } else if (durationSortMode === 'desc') {
      durationSortMode = 'asc';  // Min to max
    } else {
      durationSortMode = 'none'; // Reset to default chronological
    }
    updateSortButtonState();
    renderFilteredSummaryView();
  }

  function updateSortButtonState() {
    const btnSort = document.getElementById('btn-sort-duration');
    if (!btnSort) return;
    if (durationSortMode === 'desc') {
      btnSort.textContent = '▼';
      btnSort.classList.add('active-filter');
    } else if (durationSortMode === 'asc') {
      btnSort.textContent = '▲';
      btnSort.classList.add('active-filter');
    } else {
      btnSort.textContent = '⇅';
      btnSort.classList.remove('active-filter');
    }
  }

  function renderFilteredSummaryView() {
    if (!rawSummaryData) return;

    const tbody = document.getElementById('sum-detail-tbody');
    let filteredRows = rawSummaryData.rows.filter(r => 
      activeEquipmentFilters.has(r.equipment) && activeContentFilters.has(r.content)
    );

    // Apply sorting if active
    if (durationSortMode !== 'none') {
      filteredRows = [...filteredRows].sort((a, b) => {
        const valA = parseFloat(a.duration_min) || 0;
        const valB = parseFloat(b.duration_min) || 0;
        return durationSortMode === 'desc' ? valB - valA : valA - valB;
      });
    }

    if (filteredRows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="padding:20px; text-align:center; color:#888;">該当するデータがありません。</td></tr>';
    } else {
      tbody.innerHTML = filteredRows.map(r => {
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

    renderSummaryBarChart(filteredRows);
  }

  function renderSummaryBarChart(filteredRows) {
    if (typeof Plotly === 'undefined') {
      setTimeout(() => renderSummaryBarChart(filteredRows), 200);
      return;
    }

    if (!rawSummaryData || filteredRows.length === 0) {
      document.getElementById('sum-barchart-container').innerHTML = '<div style="display:flex; justify-content:center; align-items:center; height:100%; color:#aaa; font-size:14px;">表示するデータがありません</div>';
      return;
    }

    const dates = [...new Set(filteredRows.map(r => r.date))].sort();
    const series = [...new Map(
      filteredRows.map(r => [r.equipment + '\u0000' + r.content, {
        equipment: r.equipment,
        content: r.content
      }])
    ).values()];
    const colors = rawSummaryData.colors || {};

    const dailyMap = {};
    filteredRows.forEach(r => {
      if (!dailyMap[r.date]) dailyMap[r.date] = {};
      if (!dailyMap[r.date][r.equipment]) dailyMap[r.date][r.equipment] = {};
      const dur = parseFloat(r.duration_min) || 0;
      dailyMap[r.date][r.equipment][r.content] =
        (dailyMap[r.date][r.equipment][r.content] || 0) + dur;
    });

    const traces = series.map(({ equipment, content }) => {
      const yValues = dates.map(d => (
        dailyMap[d] && dailyMap[d][equipment] && dailyMap[d][equipment][content]
          ? dailyMap[d][equipment][content]
          : 0
      ));
      return {
        x: dates.map(d => d.replace(/-/g, '/')),
        y: yValues,
        name: equipment + ' / ' + content,
        type: 'bar',
        legendgroup: equipment,
        marker: { color: colors[content] || DEFAULT_CLR },
        hovertemplate: equipment + ' / ' + content + '<br>%{x}: %{y:.2f} 分<extra></extra>'
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

  // ── EXCEL-LIKE FILTER POPOVER LOGIC ──────────────────────────────
  function toggleFilterPopover(columnKey, event) {
    event.stopPropagation();
    const popover = document.getElementById('filter-popover');
    
    if (popover.style.display === 'flex' && currentFilterColumn === columnKey) {
      closeFilterPopover();
      return;
    }

    currentFilterColumn = columnKey;
    
    const btnRect = event.currentTarget.getBoundingClientRect();
    popover.style.top = (btnRect.bottom + 4) + 'px';
    popover.style.left = Math.min(btnRect.left, window.innerWidth - 270) + 'px';
    popover.style.display = 'flex';

    document.getElementById('filter-search-input').value = '';
    buildFilterPopoverOptions();
  }

  function buildFilterPopoverOptions() {
    if (!rawSummaryData) return;

    const listEl = document.getElementById('filter-options-list');
    const allItems = [...new Set(rawSummaryData.rows.map(r => r[currentFilterColumn]))].sort();
    const activeSet = currentFilterColumn === 'equipment' ? activeEquipmentFilters : activeContentFilters;

    listEl.innerHTML = allItems.map(item => {
      const isChecked = activeSet.has(item) ? 'checked' : '';
      return `<label><input type="checkbox" class="filter-opt-cb" value="${item}" ${isChecked}> <span>${item}</span></label>`;
    }).join('');

    updateSelectAllCheckboxState();
  }

  function filterPopoverOptions() {
    const query = document.getElementById('filter-search-input').value.toLowerCase().trim();
    const labels = document.querySelectorAll('#filter-options-list label');

    labels.forEach(label => {
      const txt = label.textContent.toLowerCase();
      label.style.display = txt.includes(query) ? 'flex' : 'none';
    });
  }

  function toggleFilterSelectAll(checked) {
    const visibleCbs = document.querySelectorAll('#filter-options-list label:not([style*="display: none"]) .filter-opt-cb');
    visibleCbs.forEach(cb => cb.checked = checked);
  }

  function updateSelectAllCheckboxState() {
    const cbs = Array.from(document.querySelectorAll('.filter-opt-cb'));
    const selectAllCb = document.getElementById('filter-select-all-cb');
    if (cbs.length === 0) return;

    const allChecked = cbs.every(cb => cb.checked);
    selectAllCb.checked = allChecked;
  }

  function applyFilterFromPopover() {
    const cbs = document.querySelectorAll('.filter-opt-cb');
    const selected = new Set();

    cbs.forEach(cb => {
      if (cb.checked) selected.add(cb.value);
    });

    if (currentFilterColumn === 'equipment') {
      activeEquipmentFilters = selected;
    } else if (currentFilterColumn === 'content') {
      activeContentFilters = selected;
    }

    closeFilterPopover();
    updateFilterHeaderButtonsState();
    renderFilteredSummaryView();
  }

  function closeFilterPopover() {
    const popover = document.getElementById('filter-popover');
    if (popover) popover.style.display = 'none';
  }

  function closeFilterPopoverOnClickOutside(event) {
    const popover = document.getElementById('filter-popover');
    if (popover && popover.style.display === 'flex' && !popover.contains(event.target)) {
      closeFilterPopover();
    }
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
                <line x1="14" y1="14" x2="14" y2="17"></line>
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

  function openDataEditor() {
    const modal = document.getElementById('data-editor-modal');
    const rowsEl = document.getElementById('editor-rows');
    const statusEl = document.getElementById('editor-status');
    rowsEl.innerHTML = '<tr><td colspan="5" class="editor-loading">読み込み中...</td></tr>';
    statusEl.textContent = '';
    document.getElementById('editor-file-label').textContent = selDate + ' / ' + selOperator;
    modal.style.display = 'flex';

    pywebview.api.get_editable_activity_data(selDate, selOperator).then(function (raw) {
      const data = JSON.parse(raw);
      if (data.error) {
        rowsEl.innerHTML = '<tr><td colspan="5" class="editor-error">' + data.error + '</td></tr>';
        return;
      }
      rowsEl.innerHTML = '';
      data.rows.forEach(row => appendEditorRow(row));
      if (data.rows.length === 0) addEditorRow();
    });
  }

  function appendEditorRow(row = {}) {
    const tr = document.createElement('tr');
    ['equipment', 'content'].forEach(key => {
      const td = document.createElement('td');
      const input = document.createElement('input');
      input.className = 'editor-input';
      input.dataset.field = key;
      input.value = row[key] || '';
      td.appendChild(input);
      tr.appendChild(td);
    });
    ['start', 'end'].forEach(key => {
      const td = document.createElement('td');
      const input = document.createElement('input');
      input.className = 'editor-input';
      input.type = 'time';
      input.step = '1';
      input.dataset.field = key;
      input.value = row[key] || '';
      td.appendChild(input);
      tr.appendChild(td);
    });
    const actionTd = document.createElement('td');
    const deleteButton = document.createElement('button');
    deleteButton.className = 'editor-delete';
    deleteButton.textContent = '削除';
    deleteButton.onclick = () => tr.remove();
    actionTd.appendChild(deleteButton);
    tr.appendChild(actionTd);
    document.getElementById('editor-rows').appendChild(tr);
  }

  function addEditorRow() {
    appendEditorRow();
  }

  function saveDataEditor() {
    if (!confirm('この内容でCSVファイルを上書き保存しますか？')) return;
    const rows = Array.from(document.querySelectorAll('#editor-rows tr')).map(tr => {
      const row = {};
      tr.querySelectorAll('input').forEach(input => row[input.dataset.field] = input.value);
      return row;
    });
    const statusEl = document.getElementById('editor-status');
    statusEl.textContent = '保存中...';
    pywebview.api.save_activity_data(selDate, selOperator, rows).then(function (response) {
      if (response.status !== 'success') {
        statusEl.textContent = response.message;
        statusEl.className = 'editor-status-error';
        return;
      }
      statusEl.className = 'editor-status-ok';
      statusEl.textContent = response.message;
      showGantt();
      setTimeout(closeDataEditor, 250);
    });
  }

  function closeDataEditor() {
    document.getElementById('data-editor-modal').style.display = 'none';
  }