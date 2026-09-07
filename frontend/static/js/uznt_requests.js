/* Заявки на перевозку (УЗнТ): список, фильтры, CRUD. */
(function () {
  'use strict';

  const $ = (sel) => document.querySelector(sel);
  const statusEl = $('#status');
  const toolbarEl = $('#toolbar');
  const contentEl = $('#content');

  const state = {
    meta: null,
    items: [],
    statuses: [],
    editingId: null,
  };

  const STATUS_BADGE = {
    new: 'new',
    accepted: 'accepted',
    in_transit: 'transit',
    delivered: 'done',
    cancelled: 'cancel',
  };

  function setStatus(text) {
    statusEl.textContent = text || '';
  }

  function errText(e) {
    if (e && e.data && e.data.errors) {
      return Object.values(e.data.errors).join('; ');
    }
    return (e && e.message) ? e.message : 'Ошибка запроса';
  }

  async function loadMeta() {
    state.meta = await UznApi.json('/api/uznt/meta');
  }

  function clientName(id) {
    const c = (state.meta && state.meta.clients || []).find((x) => x.id === id);
    return c ? c.name : (id === null || id === undefined ? '' : String(id));
  }

  function warehouseName(id) {
    const w = (state.meta && state.meta.warehouses || []).find((x) => x.id === id);
    return w ? w.name : (id === null || id === undefined ? '' : String(id));
  }

  function recent(id, list, fallback) {
    if (id === null || id === undefined || id === '') return fallback || '';
    const row = (list || []).find((x) => x.id === id);
    return row ? row.name : String(id);
  }

  function esc(v) { return UznApi.esc(v); }

  function renderFilters() {
    const opts = state.statuses.map((s) =>
      `<option value="${esc(s.code)}">${esc(s.label)}</option>`).join('');
    toolbarEl.innerHTML = `
      <form id="filters" class="uznt-filters">
        <select id="f-status" name="status"><option value="">Все статусы</option>${opts}</select>
        <input type="date" id="f-date-from" name="date_from" title="с даты">
        <input type="date" id="f-date-to" name="date_to" title="по дату">
        <select id="f-client" name="client_id"><option value="">Все клиенты</option>
          ${(state.meta ? state.meta.clients : []).map((c) =>
            `<option value="${c.id}">${esc(c.name)}</option>`).join('')}
        </select>
        <button type="submit" class="btn">Показать</button>
        <button type="button" id="btn-refresh" class="btn btn-ghost">Обновить</button>
        <button type="button" id="btn-new" class="btn btn-primary">+ Новая заявка</button>
      </form>`;

    $('#btn-new').addEventListener('click', () => openForm(null));
    $('#btn-refresh').addEventListener('click', () => load());
    $('#filters').addEventListener('submit', (e) => { e.preventDefault(); load(); });
  }

  function statusBadgeClass(code) {
    return STATUS_BADGE[code] ? ` uzn-badge--${STATUS_BADGE[code]}` : '';
  }

  function renderRows() {
    if (!state.items.length) {
      contentEl.innerHTML = '<p class="muted">Заявок нет. Создайте первую — кнопка «+ Новая заявка».</p>';
      return;
    }
    const rows = state.items.map((r) => `
      <tr>
        <td>${esc(r.number)}</td>
        <td>${esc(r.request_date)}</td>
        <td>${esc(recent(r.client_id, state.meta.clients, r.client_name))}</td>
        <td>${esc(r.from_location || '')} → ${esc(r.to_location || '')}</td>
        <td>${esc(r.cargo_name || '')}</td>
        <td class="num">${r.quantity ?? ''} ${esc(r.unit_label || r.unit || '')}</td>
        <td class="num">${r.trucks_count ?? ''}</td>
        <td class="num">${r.price == null ? '' : r.price}</td>
        <td><span class="uzn-badge${statusBadgeClass(r.status)}">${esc(r.status_label)}</span></td>
        <td>${esc(r.priority_label || '')}</td>
        <td class="uznt-actions">
          <button class="btn btn-ghost btn-sm" data-open="${r.id}">Открыть</button>
          <button class="btn btn-ghost btn-sm" data-edit="${r.id}">Изм.</button>
          <button class="btn btn-ghost btn-sm btn-danger-ghost" data-del="${r.id}">Удалить</button>
        </td>
      </tr>`).join('');

    contentEl.innerHTML = `
      <table class="uznt-table">
        <thead>
          <tr>
            <th>№</th><th>Дата</th><th>Клиент</th><th>Маршрут</th><th>Груз</th>
            <th>Кол-во</th><th>Машин</th><th>Цена</th><th>Статус</th><th>Пр.</th><th>Действия</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;

    contentEl.querySelectorAll('[data-open]').forEach((b) =>
      b.addEventListener('click', () => openForm(Number(b.dataset.open), { readonly: true })));
    contentEl.querySelectorAll('[data-edit]').forEach((b) =>
      b.addEventListener('click', () => openForm(Number(b.dataset.edit))));
    contentEl.querySelectorAll('[data-del]').forEach((b) =>
      b.addEventListener('click', () => removeRequest(Number(b.dataset.del))));
  }

  async function load() {
    try {
      if (!state.meta) await loadMeta();
      const f = new URLSearchParams();
      const status = $('#f-status') ? $('#f-status').value : '';
      const dateFrom = $('#f-date-from') ? $('#f-date-from').value : '';
      const dateTo = $('#f-date-to') ? $('#f-date-to').value : '';
      const client = $('#f-client') ? $('#f-client').value : '';
      if (status) f.set('status', status);
      if (dateFrom) f.set('date_from', dateFrom);
      if (dateTo) f.set('date_to', dateTo);
      if (client) f.set('client_id', client);

      const data = await UznApi.json('/api/uznt/requests?' + f.toString());
      state.items = data.items || [];
      state.statuses = data.statuses || [];
      if (!toolbarEl.children.length) renderFilters();
      renderRows();
      setStatus(`Заявок: ${state.items.length}`);
    } catch (e) {
      setStatus(errText(e));
      contentEl.innerHTML = `<p class="status--error">${esc(errText(e))}</p>`;
    }
  }

  function inputRow(label, control) {
    return `<label class="uznt-field"><span class="uznt-field-label">${esc(label)}</span>${control}</label>`;
  }

  function buildFormFields(r) {
    const meta = state.meta;
    const clients = meta.clients.map((c) =>
      `<option value="${c.id}"${r && r.client_id === c.id ? ' selected' : ''}>${esc(c.name)}</option>`).join('');
    const warehouses = meta.warehouses.map((w) =>
      `<option value="${w.id}"${r && r.warehouse_id === w.id ? ' selected' : ''}>${esc(w.name)}</option>`).join('');
    const vtypes = meta.vehicle_types.map((v) =>
      `<option value="${v.id}"${r && r.vehicle_type_id === v.id ? ' selected' : ''}>${esc(v.dimensions_label ? v.name + ' — ' + v.dimensions_label : v.name)}</option>`).join('');
    const units = meta.units.map((u) =>
      `<option value="${esc(u.code)}"${r && r.unit === u.code ? ' selected' : ''}>${esc(u.name)}</option>`).join('');
    const statuses = state.statuses.map((s) =>
      `<option value="${esc(s.code)}"${r && r.status === s.code ? ' selected' : ''}>${esc(s.label)}</option>`).join('');
    const priorities = meta.priorities.map((p) =>
      `<option value="${esc(p.code)}"${r && r.priority === p.code ? ' selected' : ''}>${esc(p.label)}</option>`).join('');
    const v = r || {};

    return `
      <input type="hidden" name="id" value="${v.id || ''}">
      ${inputRow('Номер (пусто — авто)', `<input name="number" value="${esc(v.number || '')}" placeholder="UZNT-…">`)}
      ${inputRow('Дата заявки', `<input type="date" name="request_date" value="${esc(v.request_date || UznApi.today())}" required>`)}
      ${inputRow('Клиент', `<select name="client_id" required><option value="">—</option>${clients}</select>`)}
      ${inputRow('Площадка', `<select name="warehouse_id" required><option value="">—</option>${warehouses}</select>`)}
      ${inputRow('Откуда', `<input name="from_location" value="${esc(v.from_location || '')}">`)}
      ${inputRow('Куда', `<input name="to_location" value="${esc(v.to_location || '')}">`)}
      ${inputRow('Груз', `<input name="cargo_name" value="${esc(v.cargo_name || '')}">`)}
      ${inputRow('Объём, м³', `<input type="number" step="0.001" name="cargo_volume_m3" value="${v.cargo_volume_m3 == null ? '' : esc(v.cargo_volume_m3)}">`)}
      ${inputRow('Вес, т', `<input type="number" step="0.001" name="cargo_weight_t" value="${v.cargo_weight_t == null ? '' : esc(v.cargo_weight_t)}">`)}
      ${inputRow('Количество', `<input type="number" step="0.001" name="quantity" value="${v.quantity == null ? 1 : esc(v.quantity)}" required>`)}
      ${inputRow('Ед. изм.', `<select name="unit">${units}</select>`)}
      ${inputRow('Тип ТС', `<select name="vehicle_type_id"><option value="">—</option>${vtypes}</select>`)}
      ${inputRow('Число машин', `<input type="number" min="1" step="1" name="trucks_count" value="${v.trucks_count == null ? 1 : esc(v.trucks_count)}" required>`)}
      ${inputRow('Цена', `<input type="number" step="0.01" name="price" value="${v.price == null ? '' : esc(v.price)}">`)}
      ${inputRow('Статус', `<select name="status">${statuses}</select>`)}
      ${inputRow('Приоритет', `<select name="priority">${priorities}</select>`)}
      ${inputRow('Примечание', `<textarea name="notes" rows="2">${esc(v.notes || '')}</textarea>`)}
    `;
  }

function openForm(id, opts = {}) {
    const readonly = Boolean(opts.readonly);
    const isNew = (id === null || id === undefined);
    const target = state.items.find((x) => x.id === id);
    const title = isNew
      ? 'Новая заявка'
      : (readonly ? 'Заявка №' + (target ? target.number : id)
        : 'Изменить заявку №' + (target ? target.number : id));

    const overlay = document.createElement('div');
    overlay.className = 'uznt-overlay';
    overlay.innerHTML = `
      <div class="uznt-dialog">
        <h3 class="uznt-dialog-title">${esc(title)}</h3>
        <form id="req-form" class="uznt-form">${buildFormFields(target)}</form>
        <div class="uznt-dialog-actions">
          <button type="button" class="btn btn-ghost" data-close>Закрыть</button>
          ${readonly ? '' : '<button type="submit" form="req-form" class="btn btn-primary">Сохранить</button>'}
        </div>
      </div>`;

    document.body.appendChild(overlay);
    overlay.querySelector('[data-close]').addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

    const form = overlay.querySelector('#req-form');
    if (readonly) {
      form.querySelectorAll('input, select, textarea').forEach((el) => (el.disabled = true));
      return;
    }
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      saveRequest(form, isNew).then(() => overlay.remove()).catch(() => {
        let box = overlay.querySelector('.uznt-dialog-error');
        if (!box) {
          box = document.createElement('div');
          box.className = 'uznt-dialog-error';
          overlay.querySelector('.uznt-dialog').insertBefore(box, overlay.querySelector('.uznt-dialog-actions'));
        }
        box.textContent = errText(lastError);
      });
    });
  }

  let lastError = null;

  function payloadFromForm(form) {
    const fd = new FormData(form);
    const payload = {};
    for (const [k, val] of fd.entries()) {
      if (String(val).trim() === '') { payload[k] = null; continue; }
      if (k === 'client_id' || k === 'warehouse_id' || k === 'vehicle_type_id' || k === 'trucks_count') {
        payload[k] = Number(val); continue;
      }
      if (k === 'cargo_volume_m3' || k === 'cargo_weight_t' || k === 'quantity' || k === 'price') {
        payload[k] = Number(val.replace(',', '.')); continue;
      }
      payload[k] = val;
    }
    delete payload.id;
    return payload;
  }

  async function saveRequest(form, isNew) {
    const payload = payloadFromForm(form);
    const url = isNew ? '/api/uznt/requests' : `/api/uznt/requests/${form.elements.id.value}`;
    try {
      await UznApi.json(url, { method: isNew ? 'POST' : 'PUT', body: JSON.stringify(payload) });
      setStatus(isNew ? 'Заявка создана.' : 'Заявка сохранена.');
      await load();
    } catch (e) {
      lastError = e;
      throw e;
    }
  }

  async function removeRequest(id) {
    const row = state.items.find((x) => x.id === id);
    const label = row ? row.number : String(id);
    if (!window.confirm(`Удалить заявку «${label}»?`)) return;
    try {
      await UznApi.json(`/api/uznt/requests/${id}`, { method: 'DELETE' });
      setStatus('Заявка удалена.');
      await load();
    } catch (e) {
      setStatus(errText(e));
      await load();
    }
  }
  load();
})();