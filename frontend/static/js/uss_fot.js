/** Отчёт «Эффективность ОХ» (УСС). */
(function initFotReportPage() {
  const statusEl = document.getElementById('status');
  const toolbarEl = document.getElementById('toolbar');
  const summaryEl = document.getElementById('summary');
  const weeklyEl = document.getElementById('weekly');
  const dailyBody = document.querySelector('#daily-table tbody');

  const moneyFmt = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  let warehouseId = null;
  let periodMonth = null;

  function setStatus(msg, isError) {
    statusEl.textContent = msg;
    statusEl.className = isError ? 'status error' : 'status';
  }

  function defaultMonth() {
    const q = UssApi.qs().get('month');
    if (q) return q;
    const d = new Date();
    d.setMonth(d.getMonth() - 1);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}`;
  }

  function fmtMoney(v) {
    return moneyFmt.format(Number(v) || 0);
  }

  function deltaClass(delta) {
    return Number(delta) >= 0 ? 'fot-delta-pos' : 'fot-delta-neg';
  }

  function goalBadge(goalMet) {
    return goalMet
      ? '<span class="fot-goal-badge fot-goal-badge--ok">≥ 0</span>'
      : '<span class="fot-goal-badge fot-goal-badge--bad">&lt; 0</span>';
  }

  function renderToolbar(warehouses) {
    toolbarEl.innerHTML = '';
    const wrap = document.createElement('div');
    wrap.className = 'toolbar';

    const whLabel = document.createElement('label');
    whLabel.className = 'fot-wh-label';
    whLabel.textContent = 'Склад ';
    const whSel = document.createElement('select');
    (warehouses || []).forEach((w) => {
      const o = document.createElement('option');
      o.value = w.id;
      o.textContent = `${w.code} — ${w.name}`;
      if (String(w.id) === String(warehouseId)) o.selected = true;
      whSel.appendChild(o);
    });
    whLabel.appendChild(whSel);

    const monthLabel = document.createElement('label');
    monthLabel.className = 'fot-wh-label';
    monthLabel.textContent = 'Период ';
    const monthInput = document.createElement('input');
    monthInput.type = 'month';
    monthInput.value = periodMonth;
    monthLabel.appendChild(monthInput);

    const hint = document.createElement('span');
    hint.className = 'muted fot-aggregate-hint';
    hint.textContent = 'Свод по всем договорам ОХ';

    whSel.addEventListener('change', () => {
      warehouseId = Number(whSel.value) || null;
      UssApi.setQs({ warehouse_id: warehouseId, month: periodMonth });
      loadReport().catch((e) => setStatus(e.message, true));
    });
    monthInput.addEventListener('change', () => {
      periodMonth = monthInput.value;
      UssApi.setQs({ warehouse_id: warehouseId, month: periodMonth });
      loadReport().catch((e) => setStatus(e.message, true));
    });

    wrap.appendChild(whLabel);
    wrap.appendChild(monthLabel);
    wrap.appendChild(hint);
    toolbarEl.appendChild(wrap);
  }

  function renderSummary(r) {
    const staffNote = r.staff_missing
      ? `<p class="fot-frozen-note muted">${r.staff_message || 'ФОТ ОХ не заполнен.'} `
        + `<a href="/admin/reference?catalog=warehouse_staff">Открыть «ФОТ ОХ»</a></p>`
      : '';
    summaryEl.innerHTML = `
      ${staffNote}
      <div class="fot-summary-cards">
        <div class="fot-card">
          <div class="fot-card-label">Операционка за месяц</div>
          <div class="fot-card-value">${fmtMoney(r.monthly_ops_revenue)} ₽</div>
        </div>
        <div class="fot-card">
          <div class="fot-card-label">ФОТ за месяц</div>
          <div class="fot-card-value">${fmtMoney(r.monthly_fot)} ₽</div>
          <div class="fot-card-sub muted">${r.staff?.length || 0} позиций · ${fmtMoney(r.daily_fot)} ₽/день</div>
        </div>
        <div class="fot-card fot-card--delta ${deltaClass(r.monthly_delta)}">
          <div class="fot-card-label">Δ месяц (операционка − ФОТ)</div>
          <div class="fot-card-value">${fmtMoney(r.monthly_delta)} ₽</div>
          <div class="fot-card-sub">${goalBadge(r.goal_met)} · договоров: ${r.contracts_count || 0}</div>
        </div>
      </div>`;
  }

  function renderWeekly(r) {
    weeklyEl.innerHTML = `
      <table class="data-table fot-weekly-table">
        <thead>
          <tr>
            <th>Нед.</th><th>Период</th><th>Дней</th>
            <th>Операционка</th><th>ФОТ</th><th>Δ</th><th>Цель</th>
          </tr>
        </thead>
        <tbody>
          ${(r.weekly || []).map((w) => `
            <tr>
              <td>${w.week}</td>
              <td>${w.from} — ${w.to}</td>
              <td>${w.days}</td>
              <td>${fmtMoney(w.ops_revenue)}</td>
              <td>${fmtMoney(w.fot)}</td>
              <td class="${deltaClass(w.delta)}">${fmtMoney(w.delta)}</td>
              <td>${goalBadge(w.goal_met)}</td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  }

  function renderDaily(r) {
    dailyBody.innerHTML = (r.daily || []).map((d) => `
      <tr class="${d.is_workday ? '' : 'fot-weekend-row'}">
        <td>${d.date}</td>
        <td>${fmtMoney(d.ops_revenue)}</td>
        <td>${fmtMoney(d.fot)}</td>
        <td class="${deltaClass(d.delta)}">${fmtMoney(d.delta)}</td>
        <td class="${deltaClass(d.cumulative_delta)}">${fmtMoney(d.cumulative_delta)}</td>
        <td>${goalBadge(d.goal_met)}</td>
      </tr>`).join('');
  }

  async function loadBootstrap() {
    const ctx = await UssApi.json('/api/uss/context?role=transport_logistics');
    const warehouses = ctx.warehouses || [];
    if (!warehouseId && warehouses.length) {
      warehouseId = warehouses[0].id;
    }
    renderToolbar(warehouses);
    return warehouses;
  }

  async function loadReport() {
    if (!warehouseId || !periodMonth) {
      setStatus('Выберите склад и период', true);
      return;
    }
    const [year, month] = periodMonth.split('-').map(Number);
    setStatus('Загрузка…');
    const q = new URLSearchParams({
      warehouse_id: warehouseId,
      year,
      month,
    });
    const r = await UssApi.json(`/api/uss/reports/fot?${q}`);
    warehouseId = r.warehouse_id || warehouseId;
    renderToolbar(r.warehouses || []);
    renderSummary(r);
    renderWeekly(r);
    renderDaily(r);
    setStatus(`Период ${periodMonth}, рабочих дней: ${r.workdays}`);
  }

  async function init() {
    periodMonth = defaultMonth();
    const qs = UssApi.qs();
    warehouseId = qs.get('warehouse_id') ? Number(qs.get('warehouse_id')) : null;
    if (qs.get('month')) periodMonth = qs.get('month');
    try {
      const warehouses = await loadBootstrap();
      if (!warehouses.length) {
        setStatus('Нет доступных складов', true);
        return;
      }
      await loadReport();
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  init();
})();
