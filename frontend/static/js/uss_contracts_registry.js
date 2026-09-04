/** Отчёт «Свод договоров и ДС». */
(function initContractsRegistryReport() {
  const statusEl = document.getElementById('status');
  const toolbarEl = document.getElementById('toolbar');
  const summaryEl = document.getElementById('summary');
  const tableWrap = document.getElementById('table-wrap');

  const STATUS_FILTER_LABELS = {
    all: 'Все',
    active_contract: 'Договор действует',
    active_amendment: 'Доп. соглашение действует',
    expiring: 'Истекают скоро',
  };

  const CONTRACT_STATUS_CLASS = {
    active: 'cr-status--ok',
    suspended: 'cr-status--warn',
    closed: 'cr-status--muted',
    draft: 'cr-status--muted',
    expired: 'cr-status--expired',
  };

  const AMENDMENT_STATUS_CLASS = {
    active: 'cr-status--ok',
    draft: 'cr-status--warn',
    superseded: 'cr-status--muted',
  };

  let warehouseId = null;
  let expiringDays = 90;
  let statusFilter = 'all';

  function setStatus(msg, isError) {
    statusEl.textContent = msg;
    statusEl.className = isError ? 'status error' : 'status';
  }

  function fmtDateRu(iso) {
    if (!iso) return '—';
    const parts = String(iso).slice(0, 10).split('-');
    if (parts.length !== 3) return iso;
    return `${parts[2]}.${parts[1]}.${parts[0]}`;
  }

  function renderToolbar(warehouses) {
    toolbarEl.innerHTML = '';
    const wrap = document.createElement('div');
    wrap.className = 'toolbar';

    const whLabel = document.createElement('label');
    whLabel.className = 'cr-filter-label';
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

    const daysLabel = document.createElement('label');
    daysLabel.className = 'cr-filter-label';
    daysLabel.textContent = 'Истекают, дн. ';
    const daysInput = document.createElement('input');
    daysInput.type = 'number';
    daysInput.min = '1';
    daysInput.max = '365';
    daysInput.value = String(expiringDays);
    daysInput.className = 'cr-days-input';
    daysLabel.appendChild(daysInput);

    const filterLabel = document.createElement('label');
    filterLabel.className = 'cr-filter-label';
    filterLabel.textContent = 'Фильтр ';
    const filterSel = document.createElement('select');
    Object.entries(STATUS_FILTER_LABELS).forEach(([value, label]) => {
      const o = document.createElement('option');
      o.value = value;
      o.textContent = label;
      if (value === statusFilter) o.selected = true;
      filterSel.appendChild(o);
    });
    filterLabel.appendChild(filterSel);

    whSel.addEventListener('change', () => {
      warehouseId = Number(whSel.value) || null;
      UssApi.setQs({ warehouse_id: warehouseId, expiring_days: expiringDays, status_filter: statusFilter });
      loadReport().catch((e) => setStatus(e.message, true));
    });
    daysInput.addEventListener('change', () => {
      expiringDays = Math.max(1, Math.min(365, Number(daysInput.value) || 90));
      daysInput.value = String(expiringDays);
      UssApi.setQs({ warehouse_id: warehouseId, expiring_days: expiringDays, status_filter: statusFilter });
      loadReport().catch((e) => setStatus(e.message, true));
    });
    filterSel.addEventListener('change', () => {
      statusFilter = filterSel.value;
      UssApi.setQs({ warehouse_id: warehouseId, expiring_days: expiringDays, status_filter: statusFilter });
      loadReport().catch((e) => setStatus(e.message, true));
    });

    wrap.appendChild(whLabel);
    wrap.appendChild(daysLabel);
    wrap.appendChild(filterLabel);
    toolbarEl.appendChild(wrap);
  }

  function statusBadge(label, cssClass) {
    return `<span class="cr-status ${cssClass || ''}">${label}</span>`;
  }

  function renderSummary(summary, days) {
    if (!summary) {
      summaryEl.innerHTML = '';
      return;
    }
    summaryEl.innerHTML = `
      <div class="cr-summary-cards">
        <article class="cr-card">
          <div class="cr-card-label">Договоров</div>
          <div class="cr-card-value">${summary.contracts_total ?? 0}</div>
        </article>
        <article class="cr-card">
          <div class="cr-card-label">Доп. соглашений</div>
          <div class="cr-card-value">${summary.amendments_total ?? 0}</div>
        </article>
        <article class="cr-card cr-card--warn">
          <div class="cr-card-label">Истекают ≤ ${days} дн.</div>
          <div class="cr-card-value">${summary.expiring_soon ?? 0}</div>
        </article>
        <article class="cr-card">
          <div class="cr-card-label">Автопролонгация</div>
          <div class="cr-card-value">${summary.auto_renew ?? 0}</div>
        </article>
      </div>`;
  }

  function renderEndCell(row) {
    if (row.end_display === '∞') {
      return '<span class="cr-infinity" title="Автопролонгация">∞</span>';
    }
    if (row.end_display === 'бессрочно') {
      return '<span class="muted">бессрочно</span>';
    }
    const days = row.days_until_end;
    let extra = '';
    if (row.expiring_soon && days !== null && days !== undefined) {
      extra = `<span class="cr-expiring">через ${days} дн.</span>`;
    }
    return `${fmtDateRu(row.effective_to)}${extra ? ` ${extra}` : ''}`;
  }

  function renderContractStatus(row) {
    const days = row.days_until_end;
    if (days !== null && days !== undefined && days < 0) {
      return statusBadge('Истёк', CONTRACT_STATUS_CLASS.expired);
    }
    const contractClass = CONTRACT_STATUS_CLASS[row.contract_status] || '';
    return statusBadge(row.contract_status_label, contractClass);
  }

  function renderTable(clients) {
    if (!clients || !clients.length) {
      tableWrap.innerHTML = '<p class="muted">Нет данных по выбранным фильтрам.</p>';
      return;
    }

    let html = '<table class="data-table cr-table"><thead><tr>';
    html += '<th>Клиент</th><th>Договор</th><th>Статус договора</th>';
    html += '<th>Доп. соглашение</th><th>Статус доп. соглашения</th><th>Действует с</th><th>Действует до</th>';
    html += '</tr></thead><tbody>';

    clients.forEach((client) => {
      (client.rows || []).forEach((row, idx) => {
        const clientCell = idx === 0
          ? `<td class="cr-client-cell" rowspan="${client.rows.length}">${row.client_name}</td>`
          : '';
        const amendmentClass = AMENDMENT_STATUS_CLASS[row.amendment_status] || 'cr-status--muted';
        html += '<tr' + (row.expiring_soon ? ' class="cr-row-expiring"' : '') + '>';
        html += clientCell;
        html += `<td>${row.contract_number || '—'}</td>`;
        html += `<td>${renderContractStatus(row)}</td>`;
        html += `<td>${row.amendment_number ? `№${row.amendment_number}` : '<span class="muted">—</span>'}</td>`;
        html += `<td>${row.amendment_id ? statusBadge(row.amendment_status_label, amendmentClass) : '<span class="muted">—</span>'}</td>`;
        html += `<td>${fmtDateRu(row.effective_from)}</td>`;
        html += `<td>${renderEndCell(row)}</td>`;
        html += '</tr>';
      });
    });

    html += '</tbody></table>';
    tableWrap.innerHTML = html;
  }

  async function loadReport() {
    setStatus('Загрузка…');
    const qs = new URLSearchParams({
      warehouse_id: warehouseId,
      expiring_days: expiringDays,
      status_filter: statusFilter,
    });
    const data = await UssApi.json(`/api/uss/reports/contracts?${qs}`);
    warehouseId = data.warehouse_id;
    expiringDays = data.expiring_days;
    statusFilter = data.status_filter || statusFilter;
    renderToolbar(data.warehouses);
    renderSummary(data.summary, data.expiring_days);
    renderTable(data.clients);
    const totalRows = (data.clients || []).reduce((n, c) => n + (c.rows || []).length, 0);
    setStatus(`Строк: ${totalRows}. Сформировано ${fmtDateRu(data.generated_at)}.`);
  }

  function initFromQs() {
    const qs = UssApi.qs();
    warehouseId = Number(qs.get('warehouse_id')) || null;
    expiringDays = Number(qs.get('expiring_days')) || 90;
    statusFilter = qs.get('status_filter') || 'all';
  }

  initFromQs();
  loadReport().catch((e) => setStatus(e.message, true));
})();
