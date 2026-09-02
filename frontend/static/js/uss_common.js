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

  renderSchemaField(fieldDef, value) {
    const f = fieldDef;
    let el;
    if (f.input_type === 'select') {
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
