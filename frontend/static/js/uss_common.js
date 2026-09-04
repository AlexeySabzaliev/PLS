/** Общие утилиты UI смен УСС */
const USS_UNIT_LABELS = {
  m2: 'м²',
  m3: 'м³',
  pcs: 'шт.',
  vehicle: 'маш.',
  hour: 'ч',
};

function ussUnitLabel(inp) {
  if (!inp) return '';
  if (inp.unit_label) return inp.unit_label;
  if (inp.unit_code && USS_UNIT_LABELS[inp.unit_code]) return USS_UNIT_LABELS[inp.unit_code];
  return inp.unit_code || '';
}

const UssApi = {
  ERROR_MESSAGES: {
    forbidden: 'Нет доступа к этому разделу',
    unauthorized: 'Войдите в систему (email и пароль)',
    no_warehouses: 'Нет доступных складов для вашего пользователя',
    period_locked: 'Период закрыт для правок',
    contract_not_found: 'Договор не найден',
    no_tariffs: 'Нет активных ставок за период',
    amendment_draft: 'ДС в статусе черновик — активируйте перед расчётом',
    amendment_dates: 'ДС не действует в выбранном периоде',
    no_tariff_rules: 'В ДС нет ставок',
    tariff_dates: 'Ставки не действуют в выбранном периоде',
    missing_params: 'Не указаны обязательные параметры',
  },

  formatError(data, fallback) {
    if (!data) return fallback || 'Ошибка запроса';
    if (data.message) return data.message;
    const code = data.error;
    if (code && this.ERROR_MESSAGES[code]) return this.ERROR_MESSAGES[code];
    return code || fallback || 'Ошибка запроса';
  },

  async json(url, options = {}) {
    const r = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      credentials: 'same-origin',
      ...options,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(this.formatError(data, `HTTP ${r.status}`));
    return data;
  },

  qs() {
    return new URLSearchParams(location.search);
  },

  setQs(params) {
    const q = new URLSearchParams(params);
    const next = `${location.pathname}?${q}`;
    if (location.search !== `?${q}`) history.replaceState(null, '', next);
    return Object.fromEntries(q);
  },

  today() {
    const n = new Date();
    const y = n.getFullYear();
    const m = String(n.getMonth() + 1).padStart(2, '0');
    const d = String(n.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  },

  isoFromDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  },

  shiftIsoDate(iso, days) {
    const d = new Date(`${iso}T12:00:00`);
    d.setDate(d.getDate() + days);
    return this.isoFromDate(d);
  },

  clampIsoDate(iso, minIso, maxIso) {
    if (!iso) return iso;
    if (minIso && iso < minIso) return minIso;
    if (maxIso && iso > maxIso) return maxIso;
    return iso;
  },

  defaultShiftDateBounds() {
    const max = this.today();
    const min = this.shiftIsoDate(max, -730);
    return { min, max };
  },

  totalsMap(rows) {
    const m = {};
    (rows || []).forEach((r) => { m[r.billing_line_code] = r.quantity; });
    return m;
  },

  renderSchemaField(fieldDef, value, options = {}) {
    const f = fieldDef;
    let el;
    if (f.input_type === 'vehicle_type') {
      el = document.createElement('select');
      el.name = f.field;
      const blank = document.createElement('option');
      blank.value = '';
      blank.textContent = '—';
      el.appendChild(blank);
      (options.vehicleTypes || []).forEach((vt) => {
        const o = document.createElement('option');
        o.value = String(vt.id);
        const dims = (vt.dimensions_label || '').trim();
        o.textContent = dims ? `${vt.name} — ${dims}` : vt.name;
        o.title = dims ? `${vt.name}, габариты ${dims} м` : vt.name;
        el.appendChild(o);
      });
      el.value = value != null && value !== '' ? String(value) : '';
    } else if (f.input_type === 'select') {
      el = document.createElement('select');
      (f.choices || []).forEach((opt) => {
        const o = document.createElement('option');
        o.value = opt.value;
        o.textContent = opt.label;
        el.appendChild(o);
      });
      el.value = value ?? '';
    } else if (f.input_type === 'time') {
      el = document.createElement('input');
      el.type = 'time';
      el.value = value ? String(value).slice(0, 5) : '';
    } else if (f.tariff_input || (f.field && f.field.startsWith('rq_'))) {
      el = document.createElement('input');
      el.type = 'number';
      el.min = '0';
      el.step = '1';
      el.value = value ?? '';
    } else {
      el = document.createElement('input');
      if (f.input_type === 'number') el.type = 'number';
      else el.type = 'text';
      el.value = value ?? '';
    }
    el.name = f.field;
    if (options.disabled) {
      el.disabled = true;
      if (el.tagName === 'INPUT' && el.type !== 'checkbox') el.readOnly = true;
    }
    return el;
  },

  mxFieldLabel(opType) {
    return opType === 'outbound' ? 'МХ-3' : 'МХ-1';
  },

  createWaybillsEditor(initialWaybills, opType, editable = true) {
    let isEditable = editable;
    let operationType = opType || 'inbound';
    const raw = (initialWaybills && initialWaybills.length) ? initialWaybills : [];
    let waybillLines = raw
      .filter((w) => (w.waybill_number || '').trim())
      .map((w) => w.waybill_number);
    let mxLines = raw
      .filter((w) => (w.mx_number || '').trim())
      .map((w) => w.mx_number);
    if (!waybillLines.length) waybillLines = [''];
    if (!mxLines.length) mxLines = [''];

    const waybillCol = document.createElement('div');
    waybillCol.className = 'waybills-col waybills-col-waybill';
    const mxCol = document.createElement('div');
    mxCol.className = 'waybills-col waybills-col-mx';

    function renderWaybills() {
      waybillCol.innerHTML = '';
      waybillLines.forEach((val, idx) => {
        const wbLine = document.createElement('div');
        wbLine.className = 'waybill-line';
        const wbInp = document.createElement('input');
        wbInp.type = 'text';
        wbInp.placeholder = '№ накладной';
        wbInp.value = val || '';
        wbInp.addEventListener('input', () => { waybillLines[idx] = wbInp.value; });
        wbLine.appendChild(wbInp);
        if (isEditable) {
          const rm = document.createElement('button');
          rm.type = 'button';
          rm.className = 'btn-link btn-remove-wb';
          rm.textContent = '×';
          rm.title = 'Удалить накладную';
          rm.addEventListener('click', () => {
            waybillLines.splice(idx, 1);
            if (!waybillLines.length) waybillLines.push('');
            renderWaybills();
          });
          wbLine.appendChild(rm);
        }
        waybillCol.appendChild(wbLine);
      });
      if (isEditable) {
        const add = document.createElement('button');
        add.type = 'button';
        add.className = 'btn-link btn-add-wb';
        add.textContent = '+ накладная';
        add.addEventListener('click', () => {
          waybillLines.push('');
          renderWaybills();
        });
        waybillCol.appendChild(add);
      }
    }

    function renderMx() {
      mxCol.innerHTML = '';
      const mxPh = UssApi.mxFieldLabel(operationType);
      mxLines.forEach((val, idx) => {
        const mxLine = document.createElement('div');
        mxLine.className = 'waybill-line';
        const mxInp = document.createElement('input');
        mxInp.type = 'text';
        mxInp.placeholder = mxPh;
        mxInp.value = val || '';
        mxInp.addEventListener('input', () => { mxLines[idx] = mxInp.value; });
        mxLine.appendChild(mxInp);
        if (isEditable) {
          const rm = document.createElement('button');
          rm.type = 'button';
          rm.className = 'btn-link btn-remove-wb';
          rm.textContent = '×';
          rm.title = 'Удалить МХ';
          rm.addEventListener('click', () => {
            mxLines.splice(idx, 1);
            if (!mxLines.length) mxLines.push('');
            renderMx();
          });
          mxLine.appendChild(rm);
        }
        mxCol.appendChild(mxLine);
      });
      if (isEditable) {
        const add = document.createElement('button');
        add.type = 'button';
        add.className = 'btn-link btn-add-wb';
        add.textContent = `+ ${mxPh}`;
        add.addEventListener('click', () => {
          mxLines.push('');
          renderMx();
        });
        mxCol.appendChild(add);
      }
    }

    function render() {
      renderWaybills();
      renderMx();
    }

    render();

    return {
      waybillCol,
      mxCol,
      setEditable(on) {
        isEditable = on;
        render();
      },
      updateOpType(newOp) {
        operationType = newOp || 'inbound';
        renderMx();
      },
      collect() {
        const n = Math.max(waybillLines.length, mxLines.length);
        const out = [];
        for (let i = 0; i < n; i += 1) {
          const waybill_number = (waybillLines[i] || '').trim();
          const mx_number = (mxLines[i] || '').trim();
          if (waybill_number || mx_number) {
            out.push({ waybill_number, mx_number });
          }
        }
        return out;
      },
    };
  },

  renderPeriodLockBanner(parent, lockInfo, monthLabel) {
    if (!lockInfo?.locked) return null;
    const el = document.createElement('div');
    el.className = 'period-lock-banner';
    const month = monthLabel ? ` ${monthLabel}` : '';
    el.textContent = `Биллинговый период${month} закрыт (${lockInfo.label || lockInfo.status}). Просмотр доступен, правки недоступны.`;
    parent.prepend(el);
    return el;
  },

  setShiftReadOnly(root, readOnly) {
    if (!root || !readOnly) return;
    root.querySelectorAll('input, select, textarea, button').forEach((el) => {
      if (el.closest('.shift-tabs')) return;
      el.disabled = true;
      if (el.tagName !== 'BUTTON') el.readOnly = true;
    });
  },

  renderContractTabs(container, tabs, options = {}) {
    if (!tabs.length) return;
    const initialIndex = Math.min(
      Math.max(0, Number(options.initialIndex) || 0),
      tabs.length - 1,
    );
    const onChange = typeof options.onChange === 'function' ? options.onChange : null;
    container.replaceChildren();
    const nav = document.createElement('div');
    nav.className = 'shift-tabs';
    nav.setAttribute('role', 'tablist');
    const panels = document.createElement('div');
    panels.className = 'shift-tab-panels';
    const panelEls = [];

    const showTab = (index, opts = {}) => {
      const safeIndex = Math.min(Math.max(0, index), tabs.length - 1);
      nav.querySelectorAll('.shift-tab').forEach((b, i) => {
        const active = i === safeIndex;
        b.classList.toggle('active', active);
        b.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      panelEls.forEach((panel, i) => {
        const active = i === safeIndex;
        if (!active) {
          panel.hidden = true;
          panel.replaceChildren();
          return;
        }
        panel.hidden = false;
        panel.replaceChildren();
        tabs[i].render(panel);
      });
      if (!opts.silent && onChange) onChange(safeIndex, tabs[safeIndex]);
    };

    tabs.forEach((tab, i) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `shift-tab${i === initialIndex ? ' active' : ''}`;
      btn.textContent = tab.label;
      btn.setAttribute('role', 'tab');
      btn.setAttribute('aria-selected', i === initialIndex ? 'true' : 'false');
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        showTab(i);
      });
      nav.appendChild(btn);
      const panel = document.createElement('div');
      panel.className = 'shift-tab-panel';
      panel.setAttribute('role', 'tabpanel');
      panel.hidden = i !== initialIndex;
      panels.appendChild(panel);
      panelEls.push(panel);
    });
    container.append(nav, panels);
    showTab(initialIndex, { silent: true });
  },

  uniqueContracts(contracts) {
    return contracts || [];
  },

  groupContractsByClient(contracts) {
    const groups = new Map();
    (contracts || []).forEach((c) => {
      const key = c.client_id != null ? String(c.client_id) : `name:${c.client_name || c.id}`;
      if (!groups.has(key)) {
        groups.set(key, {
          client_id: c.client_id,
          client_name: c.client_name || 'Без клиента',
          contracts: [],
        });
      }
      groups.get(key).contracts.push(c);
    });
    return Array.from(groups.values()).sort((a, b) =>
      (a.client_name || '').localeCompare(b.client_name || '', 'ru'),
    );
  },

  renderContractHeader(block, contractInfo) {
    const h2 = document.createElement('h2');
    h2.textContent = contractInfo.header
      || (contractInfo.amendment_number
        ? `ДС №${contractInfo.amendment_number} · договор ${contractInfo.number}`
        : `Договор ${contractInfo.number}`);
    block.appendChild(h2);
  },

  contractBlockKey(contractInfo) {
    return contractInfo.block_key || String(contractInfo.id);
  },

  _dailyReportSection(title, hint) {
    const section = document.createElement('section');
    section.className = 'uss-daily-report-section';
    const head = document.createElement('div');
    head.className = 'uss-daily-report-section-head';
    const h4 = document.createElement('h4');
    h4.className = 'uss-daily-report-section-title';
    h4.textContent = title;
    head.appendChild(h4);
    section.appendChild(head);
    if (hint) {
      const p = document.createElement('p');
      p.className = 'uss-daily-report-hint muted';
      p.textContent = hint;
      section.appendChild(p);
    }
    const body = document.createElement('div');
    body.className = 'uss-daily-report-section-body';
    section.appendChild(body);
    return { section, body };
  },

  renderPeriodForm(container, schema, totals, onSave, options = {}) {
    const inputs = schema?.period_inputs || [];
    if (!inputs.length) {
      if (!options.embedded) {
        container.innerHTML = '<p class="muted">Нет суточных полей по схеме договора.</p>';
      }
      return null;
    }
    const form = document.createElement('form');
    form.className = 'period-form uss-daily-report-fields';
    inputs.forEach((inp) => {
      const code = inp.billing_line_code;
      const row = document.createElement('label');
      row.className = 'field-row';
      const unitLbl = ussUnitLabel(inp);
      const unit = unitLbl ? ` (${unitLbl})` : '';
      row.innerHTML = `<span>${inp.name || code}${unit}</span>`;
      const el = document.createElement('input');
      el.type = 'number';
      el.step = 'any';
      el.name = code;
      el.value = totals[code] ?? '';
      row.appendChild(el);
      form.appendChild(row);
    });
    const btn = document.createElement('button');
    btn.type = 'submit';
    btn.textContent = options.saveLabel || 'Сохранить';
    form.appendChild(btn);
    if (options.readOnly) {
      form.querySelectorAll('input, button').forEach((el) => { el.disabled = true; });
    }
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const entries = inputs.map((inp) => ({
        billing_line_code: inp.billing_line_code,
        quantity: parseFloat(form.elements[inp.billing_line_code].value) || 0,
      }));
      onSave(entries);
    });
    if (!options.embedded) {
      container.innerHTML = '';
    }
    container.appendChild(form);
    return form;
  },

  _renderInventoryDailyFields(body, schema, areaEntries, extraEntries, onSave, options = {}) {
    const areas = schema?.inventory_areas || [];
    const extras = schema?.inventory_extra || [];
    const fields = [
      ...areas.map((x) => ({ ...x, bucket: 'area' })),
      ...extras.map((x) => ({ ...x, bucket: 'extra' })),
    ];
    if (!fields.length) {
      body.innerHTML = '<p class="muted">Нет полей УЗ по схеме договора.</p>';
      return;
    }
    const form = document.createElement('form');
    form.className = 'period-form uss-daily-report-fields';
    fields.forEach((inp) => {
      const code = inp.billing_line_code;
      const store = inp.bucket === 'area' ? areaEntries : extraEntries;
      const row = document.createElement('label');
      row.className = 'field-row';
      const unitLbl = ussUnitLabel(inp);
      const unit = unitLbl ? ` (${unitLbl})` : '';
      row.innerHTML = `<span>${inp.name || code}${unit}</span>`;
      const el = document.createElement('input');
      el.type = 'number';
      el.step = 'any';
      el.dataset.code = code;
      el.dataset.bucket = inp.bucket;
      el.value = store?.[code] ?? '';
      row.appendChild(el);
      form.appendChild(row);
    });
    const btn = document.createElement('button');
    btn.type = 'submit';
    btn.textContent = 'Сохранить';
    form.appendChild(btn);
    if (options.readOnly) {
      form.querySelectorAll('input, button').forEach((el) => { el.disabled = true; });
    }
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const area = { ...areaEntries };
      const extra = { ...extraEntries };
      form.querySelectorAll('input[data-code]').forEach((el) => {
        const val = parseFloat(el.value) || 0;
        if (el.dataset.bucket === 'area') area[el.dataset.code] = val;
        else extra[el.dataset.code] = val;
      });
      onSave(area, extra);
    });
    body.appendChild(form);
  },

  renderDailyReportForm(container, options = {}) {
    const {
      schema = {},
      totals = {},
      onPeriodSave,
      inventory = null,
      readOnly = false,
    } = options;
    const periodInputs = schema.period_inputs || [];
    const hasPeriod = periodInputs.length > 0 && typeof onPeriodSave === 'function';
    const hasInventory = inventory && (
      (schema.inventory_areas || []).length || (schema.inventory_extra || []).length
    );
    container.innerHTML = '';
    const root = document.createElement('div');
    root.className = 'uss-daily-report';
    const title = document.createElement('h3');
    title.className = 'uss-daily-report-title';
    title.textContent = 'Дополнительный';
    root.appendChild(title);
    const sections = document.createElement('div');
    sections.className = 'uss-daily-report-sections';
    if (hasPeriod) {
      const { section, body } = this._dailyReportSection(
        'Итоги за день',
        'Допуслуги без привязки к ТС — итог за день по договору.',
      );
      this.renderPeriodForm(body, schema, totals, onPeriodSave, {
        embedded: true,
        saveLabel: 'Сохранить',
        readOnly,
      });
      sections.appendChild(section);
    } else if (typeof onPeriodSave === 'function') {
      const { section, body } = this._dailyReportSection(
        'Итоги за день',
        'Допуслуги без привязки к ТС — итог за день по договору.',
      );
      const empty = document.createElement('p');
      empty.className = 'muted';
      empty.textContent = 'Нет полей итога за день по этому ДС. Проверьте ставки со способом «Итог за день» в справочнике.';
      body.appendChild(empty);
      sections.appendChild(section);
    }
    if (hasInventory) {
      const { section, body } = this._dailyReportSection(
        'Итоги за день',
        'Площади хранения и перетарка за день по договору.',
      );
      this._renderInventoryDailyFields(
        body,
        schema,
        inventory.areaEntries,
        inventory.extraEntries,
        inventory.onSave,
        { readOnly },
      );
      sections.appendChild(section);
    }
    root.appendChild(sections);
    if (!hasPeriod && !hasInventory && typeof onPeriodSave !== 'function') {
      const empty = document.createElement('p');
      empty.className = 'muted';
      empty.textContent = 'Нет полей суточного отчёта по схеме договора.';
      root.appendChild(empty);
    }
    container.appendChild(root);
  },

  applyContractPeriodLock(block, lockInfo, monthLabel) {
    if (!block || !lockInfo?.locked) {
      if (block) block.dataset.periodLocked = '0';
      return false;
    }
    this.renderPeriodLockBanner(block, lockInfo, monthLabel);
    block.dataset.periodLocked = '1';
    return true;
  },

  setRowFieldsEditable(rowEl, editable) {
    if (!rowEl) return;
    rowEl.classList.toggle('vehicle-row-editing', editable);
    rowEl.querySelectorAll('input, select, textarea').forEach((el) => {
      el.disabled = !editable;
      if (el.tagName === 'INPUT' && el.type !== 'checkbox') el.readOnly = !editable;
    });
    rowEl.querySelectorAll('.btn-link').forEach((el) => {
      el.disabled = !editable;
    });
  },

  async showVehicleAuditDialog(vehicleId, options = {}) {
    const data = await this.json(`/api/uss/transport/vehicles/${vehicleId}/audit`);
    const dlg = document.createElement('dialog');
    dlg.className = 'audit-dialog';
    const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;');
    const plate = options.plate ? ` · ${esc(options.plate)}` : '';
    let rows = '';
    (data.items || []).forEach((item) => {
      const when = item.created_at ? item.created_at.replace('T', ' ').slice(0, 19) : '';
      const who = esc(item.user_name || '—');
      const action = esc(item.action_label || item.action);
      const display = item.changes_display || [];
      let body = '';
      if (display.length) {
        body = '<ul class="audit-changes">' + display.map((row) =>
          `<li><span class="audit-field">${esc(row.label)}</span>: `
          + `<span class="audit-old">${esc(row.old)}</span> → `
          + `<span class="audit-new">${esc(row.new)}</span></li>`,
        ).join('') + '</ul>';
      } else if (item.summary) {
        body = `<p class="audit-summary">${esc(item.summary)}</p>`;
      }
      rows += `<li class="audit-entry"><div class="audit-entry-head"><strong>${action}</strong> · ${who}<br><span class="muted audit-when">${when}</span></div>${body}</li>`;
    });
    dlg.innerHTML = `
      <form method="dialog" class="audit-dialog-form">
        <h3>Журнал строки ТС${plate}</h3>
        <p class="muted audit-dialog-lead">Хронология действий и изменений по этой строке.</p>
        ${rows ? `<ol class="audit-list">${rows}</ol>` : '<p class="muted">Записей пока нет.</p>'}
        <div class="access-form-actions"><button type="submit" class="ref-btn ref-btn--primary">Закрыть</button></div>
      </form>`;
    document.body.appendChild(dlg);
    dlg.showModal();
    dlg.addEventListener('close', () => dlg.remove());
  },

  renderContractDateHint(parent, hint) {
    if (!hint) return;
    const el = document.createElement('p');
    el.className = 'contract-date-hint muted';
    el.textContent = hint;
    parent.appendChild(el);
  },

  renderToolbar(container, { warehouses, warehouseId, date, role, minDate, maxDate, onChange }) {
    container.innerHTML = '';
    const bounds = this.defaultShiftDateBounds();
    const minIso = minDate || bounds.min;
    const maxIso = maxDate || bounds.max;
    let currentDate = this.clampIsoDate(date || this.today(), minIso, maxIso);

    const wrap = document.createElement('div');
    wrap.className = 'toolbar';

    const whLabel = document.createElement('label');
    whLabel.textContent = 'Склад ';
    const whSel = document.createElement('select');
    whSel.id = 'wh-select';
    (warehouses || []).forEach((w) => {
      const o = document.createElement('option');
      o.value = w.id;
      o.textContent = `${w.code} — ${w.name}`;
      if (String(w.id) === String(warehouseId)) o.selected = true;
      whSel.appendChild(o);
    });
    whLabel.appendChild(whSel);

    const dateNav = document.createElement('div');
    dateNav.className = 'period-nav period-nav--day';

    const prevBtn = document.createElement('button');
    prevBtn.type = 'button';
    prevBtn.className = 'btn-icon period-nav-prev';
    prevBtn.title = 'Предыдущий день';
    prevBtn.textContent = '‹';

    const dateLabel = document.createElement('label');
    dateLabel.textContent = ' Дата ';
    const dateInp = document.createElement('input');
    dateInp.type = 'date';
    dateInp.id = 'date-input';
    dateInp.value = currentDate;
    dateInp.min = minIso;
    dateInp.max = maxIso;
    dateLabel.appendChild(dateInp);

    const nextBtn = document.createElement('button');
    nextBtn.type = 'button';
    nextBtn.className = 'btn-icon period-nav-next';
    nextBtn.title = 'Следующий день';
    nextBtn.textContent = '›';

    const todayBtn = document.createElement('button');
    todayBtn.type = 'button';
    todayBtn.className = 'btn-link period-nav-today';
    todayBtn.textContent = 'Сегодня';

    dateNav.append(prevBtn, dateLabel, nextBtn, todayBtn);

    const reload = document.createElement('button');
    reload.type = 'button';
    reload.textContent = 'Обновить';

    const fireChange = () => {
      currentDate = this.clampIsoDate(dateInp.value, minIso, maxIso);
      dateInp.value = currentDate;
      onChange({
        warehouse_id: whSel.value,
        date: currentDate,
        role,
      });
    };

    prevBtn.addEventListener('click', () => {
      dateInp.value = this.clampIsoDate(this.shiftIsoDate(dateInp.value, -1), minIso, maxIso);
      fireChange();
    });
    nextBtn.addEventListener('click', () => {
      dateInp.value = this.clampIsoDate(this.shiftIsoDate(dateInp.value, 1), minIso, maxIso);
      fireChange();
    });
    todayBtn.addEventListener('click', () => {
      dateInp.value = this.clampIsoDate(this.today(), minIso, maxIso);
      fireChange();
    });
    dateInp.addEventListener('change', fireChange);
    whSel.addEventListener('change', fireChange);
    reload.addEventListener('click', fireChange);

    wrap.append(whLabel, dateNav, reload);
    container.appendChild(wrap);
  },

  renderInventoryForm(container, schema, areaEntries, extraEntries, onSave) {
    const areas = schema?.inventory_areas || [];
    const extras = schema?.inventory_extra || [];
    const fields = [
      ...areas.map((x) => ({ ...x, bucket: 'area' })),
      ...extras.map((x) => ({ ...x, bucket: 'extra' })),
    ];
    if (!fields.length) {
      container.innerHTML = '<p class="muted">Нет полей УЗ по схеме договора.</p>';
      return;
    }
    const form = document.createElement('form');
    form.className = 'period-form';
    fields.forEach((inp) => {
      const code = inp.billing_line_code;
      const store = inp.bucket === 'area' ? areaEntries : extraEntries;
      const row = document.createElement('label');
      row.className = 'field-row';
      const unitLbl = ussUnitLabel(inp);
      const unit = unitLbl ? ` (${unitLbl})` : '';
      row.innerHTML = `<span>${inp.name || code}${unit}</span>`;
      const el = document.createElement('input');
      el.type = 'number';
      el.step = 'any';
      el.dataset.code = code;
      el.dataset.bucket = inp.bucket;
      el.value = store?.[code] ?? '';
      row.appendChild(el);
      form.appendChild(row);
    });
    const btn = document.createElement('button');
    btn.type = 'submit';
    btn.textContent = 'Сохранить';
    form.appendChild(btn);
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const area = { ...areaEntries };
      const extra = { ...extraEntries };
      form.querySelectorAll('input[data-code]').forEach((el) => {
        const val = parseFloat(el.value) || 0;
        if (el.dataset.bucket === 'area') area[el.dataset.code] = val;
        else extra[el.dataset.code] = val;
      });
      onSave(area, extra);
    });
    container.innerHTML = '';
    container.appendChild(form);
  },
};
