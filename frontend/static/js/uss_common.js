/** Общие утилиты UI смен УСС */
const UssApi = {
  async json(url, options = {}) {
    const r = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      credentials: 'same-origin',
      ...options,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
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
    return new Date().toISOString().slice(0, 10);
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
    let lines = (initialWaybills && initialWaybills.length)
      ? initialWaybills.map((w) => ({ ...w }))
      : [{ waybill_number: '', mx_number: '' }];
    let operationType = opType || 'inbound';

    const waybillCol = document.createElement('div');
    waybillCol.className = 'waybills-col waybills-col-waybill';
    const mxCol = document.createElement('div');
    mxCol.className = 'waybills-col waybills-col-mx';

    function render() {
      waybillCol.innerHTML = '';
      mxCol.innerHTML = '';
      const mxPh = UssApi.mxFieldLabel(operationType);
      lines.forEach((wb, idx) => {
        const wbLine = document.createElement('div');
        wbLine.className = 'waybill-line';
        const wbInp = document.createElement('input');
        wbInp.type = 'text';
        wbInp.placeholder = '№ накладной';
        wbInp.value = wb.waybill_number || '';
        wbInp.addEventListener('input', () => { lines[idx].waybill_number = wbInp.value; });
        wbLine.appendChild(wbInp);
        if (editable) {
          const rm = document.createElement('button');
          rm.type = 'button';
          rm.className = 'btn-link btn-remove-wb';
          rm.textContent = '×';
          rm.title = 'Удалить накладную';
          rm.addEventListener('click', () => {
            lines.splice(idx, 1);
            if (!lines.length) lines.push({ waybill_number: '', mx_number: '' });
            render();
          });
          wbLine.appendChild(rm);
        }
        waybillCol.appendChild(wbLine);

        const mxLine = document.createElement('div');
        mxLine.className = 'waybill-line';
        const mxInp = document.createElement('input');
        mxInp.type = 'text';
        mxInp.placeholder = mxPh;
        mxInp.value = wb.mx_number || '';
        mxInp.addEventListener('input', () => { lines[idx].mx_number = mxInp.value; });
        mxLine.appendChild(mxInp);
        mxCol.appendChild(mxLine);
      });
      if (editable) {
        const add = document.createElement('button');
        add.type = 'button';
        add.className = 'btn-link btn-add-wb';
        add.textContent = '+ накладная';
        add.addEventListener('click', () => {
          lines.push({ waybill_number: '', mx_number: '' });
          render();
        });
        waybillCol.appendChild(add);
      }
    }

    render();

    return {
      waybillCol,
      mxCol,
      updateOpType(newOp) {
        operationType = newOp || 'inbound';
        render();
      },
      collect() {
        return lines.map((w) => ({
          waybill_number: (w.waybill_number || '').trim(),
          mx_number: (w.mx_number || '').trim(),
        }));
      },
    };
  },

  renderPeriodForm(container, schema, totals, onSave) {
    const inputs = schema?.period_inputs || [];
    if (!inputs.length) {
      container.innerHTML = '<p class="muted">Нет суточных полей по схеме договора.</p>';
      return;
    }
    const form = document.createElement('form');
    form.className = 'period-form';
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
    btn.textContent = 'Сохранить суточные';
    form.appendChild(btn);
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const entries = inputs.map((inp) => ({
        billing_line_code: inp.billing_line_code,
        quantity: parseFloat(form.elements[inp.billing_line_code].value) || 0,
      }));
      onSave(entries);
    });
    container.innerHTML = '';
    container.appendChild(form);
  },

  renderToolbar(container, { warehouses, warehouseId, date, role, onChange }) {
    container.innerHTML = '';
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

    const dateLabel = document.createElement('label');
    dateLabel.textContent = ' Дата ';
    const dateInp = document.createElement('input');
    dateInp.type = 'date';
    dateInp.id = 'date-input';
    dateInp.value = date;
    dateLabel.appendChild(dateInp);

    const reload = document.createElement('button');
    reload.type = 'button';
    reload.textContent = 'Обновить';
    reload.addEventListener('click', () => onChange({
      warehouse_id: whSel.value,
      date: dateInp.value,
      role,
    }));

    wrap.append(whLabel, dateLabel, reload);
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
