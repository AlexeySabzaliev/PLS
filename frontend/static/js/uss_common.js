/** Общие утилиты UI смен УСС */
const UssApi = {
  ERROR_MESSAGES: {
    forbidden: 'Нет доступа к этому разделу',
    unauthorized: 'Войдите через SSO или /api/auth/login',
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
    return el;
  },

  mxFieldLabel(opType) {
    return opType === 'outbound' ? 'МХ-3' : 'МХ-1';
  },

  createWaybillsEditor(initialWaybills, opType, editable = true) {
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
        if (editable) {
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
      if (editable) {
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
        if (editable) {
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
      if (editable) {
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

  renderContractTabs(container, tabs) {
    if (!tabs.length) return;
    container.replaceChildren();
    const nav = document.createElement('div');
    nav.className = 'shift-tabs';
    const panels = document.createElement('div');
    panels.className = 'shift-tab-panels';

    const showTab = (index) => {
      nav.querySelectorAll('.shift-tab').forEach((b, i) => {
        b.classList.toggle('active', i === index);
      });
      panels.querySelectorAll('.shift-tab-panel').forEach((panel, i) => {
        const active = i === index;
        panel.classList.toggle('hidden', !active);
        if (active) {
          panel.replaceChildren();
          tabs[i].render(panel);
        }
      });
    };

    tabs.forEach((tab, i) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `shift-tab${i === 0 ? ' active' : ''}`;
      btn.textContent = tab.label;
      btn.addEventListener('click', () => showTab(i));
      nav.appendChild(btn);
      const panel = document.createElement('div');
      panel.className = `shift-tab-panel${i === 0 ? '' : ' hidden'}`;
      panels.appendChild(panel);
    });
    container.append(nav, panels);
    showTab(0);
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
      const unit = inp.unit_code ? ` (${inp.unit_code})` : '';
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

  _renderVehicleExtrasTable(body, vInputs, vehicleExtras) {
    const {
      vehicles = [],
      vehicleLabelFn,
      onSave,
    } = vehicleExtras;
    const labelFn = vehicleLabelFn || ((v) => {
      const parts = [v.tractor_plate, v.trailer_plate].filter(Boolean);
      return parts.length ? parts.join(' / ') : 'ТС';
    });
    const saved = vehicles.filter((v) => v.id);
    if (!saved.length) {
      const empty = document.createElement('p');
      empty.className = 'muted';
      empty.textContent = 'Нет сохранённых ТС — сначала добавьте и сохраните машины на вкладке «ТС».';
      body.appendChild(empty);
      return;
    }
    const wrap = document.createElement('div');
    wrap.className = 'transport-table-wrap vehicle-extras-table-wrap';
    const table = document.createElement('table');
    table.className = 'data-table vehicle-extras-table';
    const thead = document.createElement('thead');
    const hr = document.createElement('tr');
    const thVehicle = document.createElement('th');
    thVehicle.textContent = 'Тягач';
    thVehicle.className = 'col-plate';
    hr.appendChild(thVehicle);
    vInputs.forEach((inp) => {
      const th = document.createElement('th');
      const unit = inp.unit_code ? ` (${inp.unit_code})` : '';
      th.textContent = `${inp.name}${unit}`;
      th.title = inp.name;
      hr.appendChild(th);
    });
    const thAct = document.createElement('th');
    thAct.className = 'col-actions';
    hr.appendChild(thAct);
    thead.appendChild(hr);
    table.appendChild(thead);
    const tbody = document.createElement('tbody');
    saved.forEach((vehicle) => {
      const rq = vehicle.report_quantities || {};
      const tr = document.createElement('tr');
      const rqInputs = {};
      const tdLabel = document.createElement('td');
      tdLabel.className = 'col-plate vehicle-extras-label';
      tdLabel.textContent = labelFn(vehicle);
      tr.appendChild(tdLabel);
      vInputs.forEach((inp) => {
        const td = document.createElement('td');
        const el = document.createElement('input');
        el.type = 'number';
        el.min = '0';
        el.step = '1';
        el.value = rq[inp.billing_line_code] ?? '';
        rqInputs[inp.billing_line_code] = el;
        td.appendChild(el);
        tr.appendChild(td);
      });
      const tdBtn = document.createElement('td');
      tdBtn.className = 'col-actions';
      const save = document.createElement('button');
      save.type = 'button';
      save.textContent = 'Сохранить';
      save.addEventListener('click', async () => {
        const report_quantities = {};
        Object.keys(rqInputs).forEach((code) => {
          const v = rqInputs[code].value;
          if (v !== '') report_quantities[code] = Number(v);
        });
        await onSave(vehicle.id, report_quantities);
      });
      tdBtn.appendChild(save);
      tr.appendChild(tdBtn);
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
    body.appendChild(wrap);
  },

  _renderInventoryDailyFields(body, schema, areaEntries, extraEntries, onSave) {
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
      const unit = inp.unit_code ? ` (${inp.unit_code})` : '';
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
    body.appendChild(form);
  },

  renderDailyReportForm(container, options = {}) {
    const {
      schema = {},
      totals = {},
      onPeriodSave,
      vehicleExtras = null,
      inventory = null,
    } = options;
    const periodInputs = schema.period_inputs || [];
    const vInputs = schema.vehicle_inputs || [];
    const hasPeriod = periodInputs.length > 0 && typeof onPeriodSave === 'function';
    const hasVehicle = vInputs.length > 0 && vehicleExtras;
    const hasInventory = inventory && (
      (schema.inventory_areas || []).length || (schema.inventory_extra || []).length
    );
    container.innerHTML = '';
    if (!hasPeriod && !hasVehicle && !hasInventory) {
      container.innerHTML = '<p class="muted">Нет полей суточного отчёта по схеме договора.</p>';
      return;
    }
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
      });
      sections.appendChild(section);
    }
    if (hasVehicle) {
      const { section, body } = this._dailyReportSection(
        'По транспорту',
        'Дополнительные тарифицируемые поля по каждому ТС.',
      );
      this._renderVehicleExtrasTable(body, vInputs, vehicleExtras);
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
      );
      sections.appendChild(section);
    }
    root.appendChild(sections);
    container.appendChild(root);
  },

  applyContractPeriodLock(block, lockInfo, monthLabel) {
    if (!block || !lockInfo?.locked) return;
    this.renderPeriodLockBanner(block, lockInfo, monthLabel);
    this.setShiftReadOnly(block, true);
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
      const unit = inp.unit_code ? ` (${inp.unit_code})` : '';
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
