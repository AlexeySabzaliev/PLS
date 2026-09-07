/** Отчёт «Заявлено vs приехало» (УСС). */
(function initArrivalGapReport() {
  const statusEl = document.getElementById('status');
  const toolbarEl = document.getElementById('toolbar');
  const summaryEl = document.getElementById('summary');
  const dailyEl = document.getElementById('daily');
  const detailsEl = document.getElementById('details');

  const numFmt = new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 0,
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
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}`;
  }

  function renderToolbar(warehouses) {
    toolbarEl.innerHTML = '';
    const wrap = document.createElement('div');
    wrap.className = 'toolbar arrival-gap-toolbar-inner';

    const whLabel = document.createElement('label');
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
    monthLabel.textContent = ' Период ';
    const monthInp = document.createElement('input');
    monthInp.type = 'month';
    monthInp.value = periodMonth;
    monthLabel.appendChild(monthInp);

    const reloadBtn = document.createElement('button');
    reloadBtn.type = 'button';
    reloadBtn.className = 'btn-primary';
    reloadBtn.textContent = 'Показать';

    const refresh = () => {
      warehouseId = Number(whSel.value) || null;
      periodMonth = monthInp.value || periodMonth;
      UssApi.setQs({ warehouse_id: warehouseId, month: periodMonth });
      loadReport().catch((e) => setStatus(e.message, true));
    };

    whSel.addEventListener('change', refresh);
    monthInp.addEventListener('change', refresh);
    reloadBtn.addEventListener('click', refresh);

    wrap.append(whLabel, monthLabel, reloadBtn);
    toolbarEl.appendChild(wrap);
  }

  function renderSummary(r) {
    summaryEl.innerHTML = `
      <div class="billing-summary-card">
        <div class="billing-summary-label">План заявок</div>
        <div class="billing-summary-total">${numFmt.format(r.planned_total || 0)}</div>
      </div>
      <div class="billing-summary-card">
        <div class="billing-summary-label">Приехало</div>
        <div class="billing-summary-total">${numFmt.format(r.arrived_total || 0)}</div>
      </div>
      <div class="billing-summary-card">
        <div class="billing-summary-label">Не прибыло</div>
        <div class="billing-summary-total">${numFmt.format(r.no_show_total || 0)}</div>
      </div>
      <div class="billing-summary-card">
        <div class="billing-summary-label">Подтверждено</div>
        <div class="billing-summary-total">${numFmt.format(r.processed_total || 0)}</div>
      </div>
      <div class="billing-summary-card">
        <div class="billing-summary-label">Отклонение</div>
        <div class="billing-summary-total">${numFmt.format(r.gap_total || 0)}</div>
        <div class="billing-summary-meta muted">Подтверждение: ${r.confirmation_rate ?? 0}%</div>
      </div>`;
  }

  function renderDaily(r) {
    const rows = (r.daily || []).map((d) => `
      <tr>
        <td>${d.date}</td>
        <td>${d.is_confirmed_day ? 'Да' : 'Нет'}</td>
        <td class="num">${numFmt.format(d.planned || 0)}</td>
        <td class="num">${numFmt.format(d.arrived || 0)}</td>
        <td class="num">${numFmt.format(d.no_show || 0)}</td>
        <td class="num">${numFmt.format(d.processed || 0)}</td>
        <td class="num">${numFmt.format(d.gap || 0)}</td>
      </tr>`).join('');

    dailyEl.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Дата</th>
            <th>День подтверждён</th>
            <th>Заявлено</th>
            <th>Приехало</th>
            <th>Не прибыло</th>
            <th>Подтверждено</th>
            <th>Отклонение</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  function renderDetails(r) {
    if (!r.details || !r.details.length) {
      detailsEl.innerHTML = '<p class="muted">Нет строк за выбранный период.</p>';
      return;
    }

    const rows = r.details.map((d) => `
      <tr>
        <td>${d.date}</td>
        <td>${d.security_request_id || '—'}</td>
        <td>${d.contract_id || '—'}</td>
        <td>${d.source || '—'}</td>
        <td>${d.arrival_status || '—'}</td>
        <td>${d.is_arrived ? 'Да' : 'Нет'}</td>
        <td>${d.is_no_show ? 'Да' : 'Нет'}</td>
        <td>${d.is_confirmed_day ? 'Да' : 'Нет'}</td>
      </tr>`).join('');

    detailsEl.innerHTML = `
      <h3>Детализация</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>Дата</th>
            <th>Заявка охраны</th>
            <th>Договор</th>
            <th>Источник</th>
            <th>Статус</th>
            <th>Приехало</th>
            <th>Не прибыло</th>
            <th>День подтверждён</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  async function loadBootstrap() {
    const ctx = await UssApi.json('/api/uss/context?role=commercial_logistics');
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
    const qs = new URLSearchParams({
      warehouse_id: warehouseId,
      year,
      month,
    });
    const r = await UssApi.json(`/api/uss/reports/arrival-gap?${qs}`);
    warehouseId = r.warehouse_id || warehouseId;
    renderToolbar(r.warehouses || []);
    renderSummary(r);
    renderDaily(r);
    renderDetails(r);
    setStatus(`Период ${periodMonth}: заявлено ${r.planned_total || 0}, приехало ${r.arrived_total || 0}.`);
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
