/** Admin UI справочников — generic CRUD по /api/reference */
(function initReferenceAdmin() {
  const statusEl = document.getElementById('status');
  const navEl = document.getElementById('catalog-nav');
  const panelEl = document.getElementById('catalog-panel');

  const LABELS = {
    clients: 'Клиенты',
    warehouses: 'Склады',
    product_types: 'Типы продукта',
    contracts: 'Договоры',
    amendments: 'Доп. соглашения',
    units: 'Единицы измерения',
    tariff_rules: 'Ставки (tariff_rules)',
    staff: 'Должности',
    vehicles: 'ТС (госномера)',
    roles: 'Роли',
  };

  const FIELD_LABELS = {
    id: 'ID',
    name: 'Наименование',
    code: 'Код',
    security_name: 'Имя в СБ',
    security_visit_place: 'Место визита СБ',
    is_active: 'Активен',
    client_id: 'Клиент ID',
    warehouse_id: 'Склад ID',
    product_type_id: 'Тип продукта ID',
    number: 'Номер',
    status: 'Статус',
    contract_id: 'Договор ID',
    effective_from: 'Действует с',
    effective_to: 'Действует до',
    billing_line_code: 'Код строки',
    amendment_id: 'ДС ID',
    unit_id: 'Ед. изм. ID',
    report_role: 'Роль отчёта',
    report_scope: 'Область',
    quantity_source: 'Источник кол-ва',
    is_custom: 'Кастом',
    price_agreed: 'Цена согласована',
    sort_order: 'Порядок',
    valid_from: 'Ставка с',
    valid_to: 'Ставка до',
    plate_number: 'Гос. номер',
    vehicle_type: 'Тип ТС',
  };

  let meta = [];
  let current = null;
  let items = [];

  function setStatus(msg, isError) {
    statusEl.textContent = msg;
    statusEl.className = isError ? 'status error' : 'status';
  }

  async function api(url, options = {}) {
    const r = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      credentials: 'same-origin',
      ...options,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
    return data;
  }

  function esc(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;');
  }

  function inputType(field, readOnly) {
    if (field === 'id' || readOnly) return 'text';
    if (field.startsWith('is_') || field === 'price_agreed') return 'checkbox';
    if (field.endsWith('_from') || field.endsWith('_to')) return 'date';
    if (field.endsWith('_id') || field === 'sort_order') return 'number';
    return 'text';
  }

  function renderNav() {
    navEl.innerHTML = '';
    meta.forEach((c) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = c.code === current ? 'active' : '';
      btn.textContent = LABELS[c.code] || c.code;
      btn.addEventListener('click', () => selectCatalog(c.code));
      navEl.appendChild(btn);
    });
  }

  function renderTable() {
    const cat = meta.find((c) => c.code === current);
    if (!cat) return;
    const fields = cat.fields.filter((f) => f !== 'id' || true);
    const readOnly = cat.read_only;

    let html = `<h2>${esc(LABELS[current] || current)}</h2>`;
    if (readOnly) {
      html += '<p class="muted">Только просмотр</p>';
    }

    html += '<div class="table-wrap"><table class="data-table"><thead><tr>';
    fields.forEach((f) => {
      html += `<th>${esc(FIELD_LABELS[f] || f)}</th>`;
    });
    if (!readOnly) html += '<th></th>';
    html += '</tr></thead><tbody>';

    items.forEach((row) => {
      html += `<tr data-id="${row.id}">`;
      fields.forEach((f) => {
        const type = inputType(f, readOnly || f === 'id');
        const val = row[f];
        if (type === 'checkbox') {
          const chk = val ? 'checked' : '';
          html += `<td><input type="checkbox" data-field="${f}" ${chk} ${readOnly || f === 'id' ? 'disabled' : ''}></td>`;
        } else {
          html += `<td><input type="${type}" data-field="${f}" value="${esc(val ?? '')}" ${readOnly || f === 'id' ? 'readonly' : ''}></td>`;
        }
      });
      if (!readOnly) {
        html += `<td class="row-actions">
          <button type="button" class="btn-save">Сохранить</button>
          <button type="button" class="btn-del">Удалить</button>
        </td>`;
      }
      html += '</tr>';
    });
    html += '</tbody></table></div>';

    if (!readOnly) {
      html += '<h3>Добавить</h3><form id="add-form" class="add-form">';
      cat.fields.filter((f) => f !== 'id').forEach((f) => {
        const type = inputType(f, false);
        const req = ['name', 'code', 'number', 'billing_line_code', 'plate_number', 'valid_from', 'effective_from'].includes(f);
        if (type === 'checkbox') {
          html += `<label class="field-row"><span>${esc(FIELD_LABELS[f] || f)}</span><input type="checkbox" name="${f}"></label>`;
        } else {
          html += `<label class="field-row"><span>${esc(FIELD_LABELS[f] || f)}</span><input type="${type}" name="${f}" ${req ? 'required' : ''}></label>`;
        }
      });
      html += '<button type="submit">Создать</button></form>';
    }

    panelEl.innerHTML = html;

    panelEl.querySelectorAll('.btn-save').forEach((btn) => {
      btn.addEventListener('click', () => saveRow(btn.closest('tr')));
    });
    panelEl.querySelectorAll('.btn-del').forEach((btn) => {
      btn.addEventListener('click', () => deleteRow(btn.closest('tr')));
    });
    const addForm = document.getElementById('add-form');
    if (addForm) addForm.addEventListener('submit', onAdd);
  }

  function rowPayload(tr) {
    const payload = {};
    tr.querySelectorAll('[data-field]').forEach((el) => {
      const f = el.dataset.field;
      if (f === 'id') return;
      if (el.type === 'checkbox') payload[f] = el.checked;
      else if (el.value !== '') payload[f] = el.value;
      else payload[f] = null;
    });
    return payload;
  }

  async function saveRow(tr) {
    const id = tr.dataset.id;
    try {
      await api(`/api/reference/${current}/${id}`, {
        method: 'PUT',
        body: JSON.stringify(rowPayload(tr)),
      });
      setStatus('Сохранено.');
      await loadItems();
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function deleteRow(tr) {
    const id = tr.dataset.id;
    if (!confirm(`Удалить запись #${id}?`)) return;
    try {
      await api(`/api/reference/${current}/${id}`, { method: 'DELETE' });
      setStatus('Удалено.');
      await loadItems();
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function onAdd(e) {
    e.preventDefault();
    const form = e.target;
    const payload = {};
    form.querySelectorAll('[name]').forEach((el) => {
      if (el.type === 'checkbox') payload[el.name] = el.checked;
      else if (el.value !== '') payload[el.name] = el.value;
    });
    try {
      await api(`/api/reference/${current}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setStatus('Создано.');
      form.reset();
      await loadItems();
    } catch (err) {
      setStatus(err.message, true);
    }
  }

  async function loadItems() {
    const data = await api(`/api/reference/${current}`);
    items = data.items || [];
    renderTable();
  }

  async function selectCatalog(code) {
    current = code;
    renderNav();
    setStatus('Загрузка…');
    try {
      await loadItems();
      setStatus(`${LABELS[code] || code}: ${items.length} записей`);
    } catch (e) {
      setStatus(e.message, true);
      panelEl.innerHTML = '';
    }
  }

  async function init() {
    try {
      const data = await api('/api/reference/meta');
      meta = data.catalogs || [];
      if (!meta.length) {
        setStatus('Нет доступных справочников.', true);
        return;
      }
      renderNav();
      await selectCatalog(meta[0].code);
    } catch (e) {
      setStatus(e.message === 'unauthorized' ? 'Войдите через SSO или /api/auth/login' : e.message, true);
    }
  }

  init();
})();
