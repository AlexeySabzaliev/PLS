/** Расчёт биллинга по договору (УСС). */
(function initBillingPage() {
  const statusEl = document.getElementById('status');
  const toolbarEl = document.getElementById('toolbar');
  const summaryEl = document.getElementById('summary');
  const contentEl = document.getElementById('content');

  const moneyFmt = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const qtyFmt = new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 3,
  });
  let isAdmin = false;
  let currentPeriod = null;
  const UNIT_LABELS = {
    m2: 'м²',
    m3: 'м³',
    pcs: 'шт.',
    vehicle: 'маш.',
    hour: 'ч',
  };

  function setStatus(msg, isError) {
    statusEl.textContent = msg;
    statusEl.className = isError ? 'status error' : 'status';
  }

  function monthBounds(ym) {
    const [y, m] = ym.split('-').map(Number);
    const last = new Date(y, m, 0).getDate();
    const mm = String(m).padStart(2, '0');
    return {
      period_from: `${y}-${mm}-01`,
      period_to: `${y}-${mm}-${String(last).padStart(2, '0')}`,
    };
  }

  function defaultMonth() {
    const q = UssApi.qs().get('month');
    if (q) return q;
    const n = new Date();
    const y = n.getFullYear();
    const m = String(n.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}`;
  }

  function renderPeriodBadge(host) {
    const existing = host.querySelector('.billing-period-badge');
    if (existing) existing.remove();
    if (!currentPeriod) return;
    const badge = document.createElement('div');
    badge.className = `billing-period-badge${currentPeriod.locked ? ' locked' : ''}`;
    badge.textContent = `Статус периода: ${currentPeriod.label || currentPeriod.status}`;
    host.appendChild(badge);
  }

  async function fetchPeriod(contractId, month) {
    const [year, m] = month.split('-').map(Number);
    currentPeriod = await UssApi.json(
      `/api/billing/period?contract_id=${contractId}&year=${year}&month=${m}`,
    );
    return currentPeriod;
  }

  async function lockPeriod(contractId, month, totalExVat) {
    const [year, m] = month.split('-').map(Number);
    const body = { contract_id: Number(contractId), year, month };
    if (totalExVat != null) body.total_ex_vat = totalExVat;
    const res = await UssApi.json('/api/billing/period/lock', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    currentPeriod = res.period;
  }

  async function unlockPeriod(contractId, month) {
    const [year, m] = month.split('-').map(Number);
    const res = await UssApi.json('/api/billing/period/unlock', {
      method: 'POST',
      body: JSON.stringify({ contract_id: Number(contractId), year, month: m }),
    });
    currentPeriod = res.period;
  }

  function renderToolbar({ warehouses, warehouseId, month, contracts, contractId, onChange, onCalculate, onLock, onUnlock }) {
    toolbarEl.innerHTML = '';
    const wrap = document.createElement('div');
    wrap.className = 'toolbar billing-toolbar';

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
    monthInp.value = month;
    monthLabel.appendChild(monthInp);

    const contractLabel = document.createElement('label');
    contractLabel.textContent = ' Договор ';
    const contractSel = document.createElement('select');
    (contracts || []).forEach((c) => {
      const o = document.createElement('option');
      o.value = c.id;
      o.textContent = c.number;
      if (String(c.id) === String(contractId)) o.selected = true;
      contractSel.appendChild(o);
    });
    contractLabel.appendChild(contractSel);

    const calcBtn = document.createElement('button');
    calcBtn.type = 'button';
    calcBtn.className = 'btn-primary';
    calcBtn.textContent = 'Рассчитать';
    calcBtn.addEventListener('click', () => onCalculate({
      warehouse_id: whSel.value,
      month: monthInp.value,
      contract_id: contractSel.value,
    }));

    const lockBtn = document.createElement('button');
    lockBtn.type = 'button';
    lockBtn.textContent = 'Закрыть период';
    lockBtn.title = 'Блокировка правок в сменах и пересчёта';
    lockBtn.addEventListener('click', () => onLock({
      warehouse_id: whSel.value,
      month: monthInp.value,
      contract_id: contractSel.value,
    }));

    const unlockBtn = document.createElement('button');
    unlockBtn.type = 'button';
    unlockBtn.textContent = 'Открыть период';
    unlockBtn.className = 'btn-secondary';
    unlockBtn.addEventListener('click', () => onUnlock({
      warehouse_id: whSel.value,
      month: monthInp.value,
      contract_id: contractSel.value,
    }));

    const reloadBtn = document.createElement('button');
    reloadBtn.type = 'button';
    reloadBtn.textContent = 'Обновить';
    reloadBtn.addEventListener('click', () => onChange({
      warehouse_id: whSel.value,
      month: monthInp.value,
      contract_id: contractSel.value,
    }));

    const exportBtn = document.createElement('button');
    exportBtn.type = 'button';
    exportBtn.className = 'btn-secondary';
    exportBtn.textContent = 'Экспорт Excel';
    exportBtn.title = 'Скачать расчёт в формате для согласования с клиентом';
    exportBtn.addEventListener('click', () => {
      const [y, m] = monthInp.value.split('-').map(Number);
      if (!contractSel.value || !y || !m) return;
      const url = `/api/billing/export?contract_id=${contractSel.value}&year=${y}&month=${m}`;
      window.location.href = url;
    });

    wrap.append(whLabel, monthLabel, contractLabel, reloadBtn, calcBtn, exportBtn, lockBtn);
    if (isAdmin) wrap.appendChild(unlockBtn);
    toolbarEl.appendChild(wrap);
    renderPeriodBadge(toolbarEl);
  }

  function renderSummary(result) {
    if (!result || result.status !== 'ok') {
      summaryEl.classList.add('hidden');
      summaryEl.innerHTML = '';
      return;
    }
    summaryEl.classList.remove('hidden');
    summaryEl.innerHTML = `
      <div class="billing-summary-card">
        <div class="billing-summary-label">Итого без НДС</div>
        <div class="billing-summary-total">${moneyFmt.format(result.total_ex_vat)} ₽</div>
        <div class="billing-summary-meta muted">
          ${result.period_from} — ${result.period_to}
        </div>
      </div>`;
  }

  function renderLines(lines) {
    contentEl.innerHTML = '';
    if (!lines?.length) {
      contentEl.innerHTML = '<p class="muted">Нет начислений за период.</p>';
      return;
    }

    const table = document.createElement('table');
    table.className = 'data-table billing-table';
    table.innerHTML = `
      <thead>
        <tr>
          <th class="col-num">№</th>
          <th>Наименование</th>
          <th class="col-qty">Кол-во</th>
          <th class="col-unit">Ед.</th>
          <th class="col-rate">Ставка</th>
          <th class="col-amount">Сумма</th>
          <th class="col-toggle"></th>
        </tr>
      </thead>`;
    const tbody = document.createElement('tbody');

    lines.forEach((line, idx) => {
      const tr = document.createElement('tr');
      tr.dataset.lineCode = line.line_code;
      const unit = UNIT_LABELS[line.unit_code] || line.unit_code || '—';
      const hasDetails = Array.isArray(line.details) && line.details.length > 0;
      tr.innerHTML = `
        <td class="col-num">${idx + 1}</td>
        <td>
          <div class="billing-line-name">${line.name || line.line_code}</div>
          ${line.formula_comment ? `<div class="muted billing-formula">${line.formula_comment}</div>` : ''}
        </td>
        <td class="col-qty num">${qtyFmt.format(line.quantity)}</td>
        <td class="col-unit">${unit}</td>
        <td class="col-rate num">${line.tariff != null ? moneyFmt.format(line.tariff) : '—'}</td>
        <td class="col-amount num"><strong>${moneyFmt.format(line.amount_ex_vat)}</strong></td>
        <td class="col-toggle">${hasDetails ? '<button type="button" class="btn-link btn-details" title="Детализация">▸</button>' : ''}</td>`;
      tbody.appendChild(tr);

      if (hasDetails) {
        const detailTr = document.createElement('tr');
        detailTr.className = 'billing-details-row hidden';
        const td = document.createElement('td');
        td.colSpan = 7;
        const list = document.createElement('ul');
        list.className = 'billing-details-list';
        line.details.forEach((d) => {
          const li = document.createElement('li');
          const amt = d.amount != null ? ` — ${moneyFmt.format(d.amount)} ₽` : '';
          li.textContent = `${d.description || d.date || ''}: ${qtyFmt.format(d.quantity)}${amt}`;
          list.appendChild(li);
        });
        td.appendChild(list);
        detailTr.appendChild(td);
        tbody.appendChild(detailTr);

        tr.querySelector('.btn-details')?.addEventListener('click', () => {
          const open = detailTr.classList.toggle('hidden');
          tr.querySelector('.btn-details').textContent = open ? '▸' : '▾';
        });
      }
    });

    table.appendChild(tbody);
    const wrap = document.createElement('section');
    wrap.className = 'contract-block';
    wrap.appendChild(table);
    contentEl.appendChild(wrap);
  }

  async function calculate(contractId, month) {
    const bounds = monthBounds(month);
    setStatus('Расчёт…');
    try {
      const result = await UssApi.json('/api/billing/calculate', {
        method: 'POST',
        body: JSON.stringify({
          contract_id: Number(contractId),
          period_from: bounds.period_from,
          period_to: bounds.period_to,
        }),
      });
      if (result.status !== 'ok') {
        setStatus(UssApi.formatError(result, 'Ошибка расчёта'), true);
        renderSummary(null);
        contentEl.innerHTML = '';
        return;
      }
      renderSummary(result);
      renderLines(result.lines);
      if (result.period) currentPeriod = result.period;
      renderPeriodBadge(toolbarEl);
      setStatus(`Расчёт выполнен: ${result.lines.length} строк.`);
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function load(opts = {}) {
    const q = UssApi.qs();
    const month = opts.month || q.get('month') || defaultMonth();
    let warehouseId = opts.warehouse_id || q.get('warehouse_id');
    let contractId = opts.contract_id || q.get('contract_id');

    setStatus('Загрузка…');
    try {
      const ctx = await UssApi.json(
        `/api/billing/context${warehouseId ? `?warehouse_id=${warehouseId}` : ''}`,
      );
      isAdmin = Boolean(ctx.is_admin);
      warehouseId = String(ctx.warehouse_id);
      if (!contractId && ctx.contracts?.length) {
        contractId = String(ctx.contracts[0].id);
      }
      UssApi.setQs({ warehouse_id: warehouseId, month, contract_id: contractId || '' });

      if (contractId) {
        await fetchPeriod(contractId, month);
      }

      const renderToolbarFn = () => renderToolbar({
        warehouses: ctx.warehouses,
        warehouseId,
        month,
        contracts: ctx.contracts,
        contractId,
        onChange: (p) => load(p),
        onCalculate: (p) => {
          UssApi.setQs(p);
          calculate(p.contract_id, p.month);
        },
        onLock: async (p) => {
          try {
            await lockPeriod(p.contract_id, p.month);
            setStatus('Период закрыт для правок.');
            renderPeriodBadge(toolbarEl);
          } catch (e) {
            setStatus(e.message, true);
          }
        },
        onUnlock: async (p) => {
          try {
            await unlockPeriod(p.contract_id, p.month);
            setStatus('Период открыт.');
            renderPeriodBadge(toolbarEl);
          } catch (e) {
            setStatus(e.message, true);
          }
        },
      });
      renderToolbarFn();

      if (!ctx.contracts?.length) {
        setStatus('Нет активных договоров ОХ на складе.');
        summaryEl.classList.add('hidden');
        contentEl.innerHTML = '';
        return;
      }
      setStatus('Выберите период и нажмите «Рассчитать».');
    } catch (e) {
      setStatus(
        e.message === 'unauthorized'
          ? UssApi.ERROR_MESSAGES.unauthorized
          : e.message,
        true,
      );
    }
  }

  load();
})();
