/** Admin UI справочников — CRUD с режимом редактирования и выпадающими списками */
(function initReferenceAdmin() {
  const statusEl = document.getElementById('status');
  const hintEl = document.getElementById('catalog-hint');
  const navEl = document.getElementById('catalog-nav');
  const panelEl = document.getElementById('catalog-panel');

  let meta = [];
  let current = null;
  let items = [];
  let lookups = {};
  let showAdvanced = false;
  const editingRows = new Set();
  const editingAmendments = new Set();
  const pendingNewRows = new Set();
  const expandedClients = new Set();
  const expandedAmendments = new Set();
  let tariffExpandCaptured = false;

  const ROLE_LABELS = {
    transport_logistics: 'Транспортная логистика',
    warehouse_logistics: 'Складская логистика',
    inventory_management: 'Управление запасами',
  };

  const QUANTITY_SOURCE_LABELS = {
    auto_contract_param: 'Система: параметр договора',
    auto_vehicle: 'Система: из транспорта',
    manual_vehicle: 'Ручной ввод в строке ТС',
    manual_daily: 'Ручной ввод: суточные допы',
    manual_inventory: 'Ручной ввод: упр. запасами',
    none: 'Не вводится',
  };

  const TARIFF_HIDDEN_FIELDS = new Set(['contract_id', 'amendment_id', 'is_custom']);

  function setStatus(msg, isError) {
    statusEl.textContent = msg;
    statusEl.className = isError ? 'status error' : 'status';
  }

  function setHintVisible(visible) {
    if (hintEl) hintEl.classList.toggle('hidden', !visible);
  }

  async function api(url, options = {}) {
    const r = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      credentials: 'same-origin',
      ...options,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      const msg = data.message || data.error;
      if (msg) throw new Error(msg);
      if (r.status === 404) {
        throw new Error(`Маршрут API не найден: ${options.method || 'GET'} ${url}. Перезапустите сервер приложения.`);
      }
      throw new Error(`HTTP ${r.status}`);
    }
    return data;
  }

  function esc(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;');
  }

  function catMeta() {
    return meta.find((c) => c.code === current) || {};
  }

  function visibleFields(cat) {
    const all = (cat.field_meta || []).map((f) => f.field);
    if (showAdvanced) return all;
    return all.filter((f) => {
      const m = cat.field_meta.find((x) => x.field === f);
      return !m?.advanced;
    });
  }

  function tariffTableFields(cat, { includeBillingLine = false } = {}) {
    let fields = visibleFields(cat).filter((f) => !TARIFF_HIDDEN_FIELDS.has(f));
    if (includeBillingLine && !fields.includes('billing_line_code')) {
      const nameIdx = fields.indexOf('name');
      const at = nameIdx >= 0 ? nameIdx + 1 : fields.length;
      fields = [...fields.slice(0, at), 'billing_line_code', ...fields.slice(at)];
    }
    return fields;
  }

  function lookupOptions(lookupKey, row) {
    let list = lookups[lookupKey] || [];
    if (lookupKey === 'amendments' && row?.contract_id) {
      list = list.filter((x) => x.contract_id === row.contract_id);
    }
    return list;
  }

  function lookupLabel(lookupKey, id) {
    if (id == null || id === '') return '—';
    const numId = Number(id);
    const hit = (lookups[lookupKey] || []).find((x) => Number(x.id) === numId);
    if (hit) return hit.label;
    if (lookupKey === 'units') {
      const byCode = (lookups.units || []).find((x) => x.code === String(id));
      if (byCode) return byCode.label;
    }
    return String(id);
  }

  function choiceLabel(fm, val) {
    if (!fm?.choices?.length) return null;
    const hit = fm.choices.find((c) => String(c.value ?? '') === String(val ?? ''));
    return hit ? hit.label : null;
  }

  function billingLineFieldMeta() {
    return catMeta().field_meta?.find((x) => x.field === 'billing_line_code');
  }

  function billingLineChoice(code) {
    const fm = billingLineFieldMeta();
    if (!fm?.choices) return null;
    return fm.choices.find((c) => c.value === code) || null;
  }

  function billingLineSelectHtml(fm, val, disabled, { nameAttr = '' } = {}) {
    const cur = String(val ?? '');
    const known = new Set((fm.choices || []).map((c) => c.value));
    let html = `<select data-field="billing_line_code" class="ref-billing-line-select"${nameAttr} ${disabled ? 'disabled' : ''}>`;
    html += `<option value=""${cur === '' ? ' selected' : ''}>— авто по наименованию —</option>`;
    (fm.choices || []).forEach((c) => {
      const sel = cur === c.value ? ' selected' : '';
      html += `<option value="${esc(c.value)}"${sel}>${esc(c.label)}</option>`;
    });
    if (cur && !known.has(cur)) {
      html += `<option value="${esc(cur)}" selected>${esc(cur)} (текущий)</option>`;
    }
    html += '</select>';
    return html;
  }

  function applyBillingLinePreview(container, code) {
    if (!code || !container) return;
    const choice = billingLineChoice(code);
    if (!choice) return;
    const setSelect = (field, value) => {
      const el = container.querySelector(`[data-field="${field}"]`)
        || container.querySelector(`[name="${field}"]`);
      if (!el || el.tagName !== 'SELECT') return;
      el.value = value == null ? '' : String(value);
    };
    if (choice.unit_code) {
      const unit = (lookups.units || []).find((u) => u.code === choice.unit_code);
      if (unit) setSelect('unit_id', unit.id);
    }
    if (choice.quantity_source) setSelect('quantity_source', choice.quantity_source);
    if (choice.report_role) setSelect('report_role', choice.report_role);
    if (choice.report_scope) setSelect('report_scope', choice.report_scope);
  }

  function bindBillingLineCodeHandlers() {
    panelEl.querySelectorAll('.ref-billing-line-select').forEach((sel) => {
      sel.addEventListener('change', () => {
        const container = sel.closest('tr') || sel.closest('form');
        if (container) applyBillingLinePreview(container, sel.value);
      });
    });
  }

  function displayReportRole(fm, row) {
    const val = row.report_role;
    if (val) {
      const label = choiceLabel(fm, val) || ROLE_LABELS[val];
      if (label) return esc(label);
    }
    const qs = (row.quantity_source || '').trim();
    if (qs === 'auto_contract_param' || qs === 'auto_vehicle' || qs === 'none') {
      const label = QUANTITY_SOURCE_LABELS[qs];
      if (label) return `<span class="ref-auto-badge">${esc(label)}</span>`;
    }
    if (!val && !qs) return '<span class="muted">—</span>';
    return esc(val || '—');
  }

  function displayQuantitySource(fm, row) {
    const val = row.quantity_source;
    if (!val) return '<span class="muted">—</span>';
    const label = choiceLabel(fm, val) || QUANTITY_SOURCE_LABELS[val];
    return esc(label || val);
  }

  function fieldCellHtml(fm, row, readOnly, rowEditing) {
    const f = fm.field;
    const val = row[f];
    const disabled = readOnly || fm.readonly || !rowEditing;

    if (fm.lookup) {
      const opts = lookupOptions(fm.lookup, row);
      let html = `<select data-field="${f}" ${disabled ? 'disabled' : ''}>`;
      html += '<option value="">—</option>';
      opts.forEach((o) => {
        const sel = Number(val) === o.id ? ' selected' : '';
        html += `<option value="${o.id}"${sel}>${esc(o.label)}</option>`;
      });
      html += '</select>';
      return html;
    }

    if (fm.type === 'bool') {
      const chk = val ? 'checked' : '';
      return `<input type="checkbox" data-field="${f}" ${chk} ${disabled ? 'disabled' : ''}>`;
    }

    if (fm.type === 'select' && fm.choices) {
      if (f === 'billing_line_code') {
        return billingLineSelectHtml(fm, val, disabled);
      }
      let html = `<select data-field="${f}" ${disabled ? 'disabled' : ''}>`;
      fm.choices.forEach((c) => {
        const sel = String(val ?? '') === String(c.value) ? ' selected' : '';
        html += `<option value="${esc(c.value)}"${sel}>${esc(c.label)}</option>`;
      });
      html += '</select>';
      return html;
    }

    if (fm.type === 'date') {
      return `<input type="date" data-field="${f}" value="${esc(val ?? '')}" ${disabled ? 'readonly' : ''}>`;
    }

    if (f === 'rate_ex_vat') {
      return `<input type="number" step="0.0001" data-field="${f}" value="${esc(val ?? '')}" ${disabled ? 'readonly' : ''}>`;
    }

    return `<input type="text" data-field="${f}" value="${esc(val ?? '')}" ${disabled ? 'readonly' : ''}>`;
  }

  function formatDateRu(iso) {
    if (!iso) return '';
    const parts = String(iso).slice(0, 10).split('-');
    if (parts.length !== 3) return String(iso);
    return `${parts[2]}.${parts[1]}.${parts[0]}`;
  }

  function amendmentMap() {
    return Object.fromEntries((lookups.amendments || []).map((a) => [a.id, a]));
  }

  function isUnlinkedAmendmentKey(amKey, amMap) {
    if (amKey === 'no_am') return true;
    return !amMap[Number(amKey)];
  }

  function amendmentDisplayLabel(am, unlinked) {
    if (!am || unlinked) return 'без ДС';
    let label = `ДС №${am.number || am.id}`;
    const from = formatDateRu(am.effective_from);
    const to = formatDateRu(am.effective_to);
    if (from) {
      label += to ? ` (${from} — ${to})` : ` (с ${from})`;
    }
    return label;
  }

  function contractPrimaryLabel(c) {
    if (!c?.label) return '';
    const parts = c.label.split(' — ');
    return parts[0] || c.label;
  }

  function contractSecondaryLabel(c) {
    if (!c?.label) return '';
    const parts = c.label.split(' — ');
    return parts.length > 1 ? parts[1] : '';
  }

  function captureTariffExpandState() {
    if (!panelEl?.querySelector('.ref-client-group')) return;
    expandedClients.clear();
    expandedAmendments.clear();
    panelEl.querySelectorAll('.ref-client-group').forEach((el) => {
      if (el.open && el.dataset.clientKey) expandedClients.add(el.dataset.clientKey);
    });
    panelEl.querySelectorAll('.ref-am-group').forEach((el) => {
      const clientKey = el.closest('.ref-client-group')?.dataset.clientKey;
      if (el.open && clientKey && el.dataset.amendmentKey) {
        expandedAmendments.add(`${clientKey}|${el.dataset.amendmentKey}`);
      }
    });
    tariffExpandCaptured = true;
  }

  function isClientOpen(clientKey) {
    if (!tariffExpandCaptured) return true;
    return expandedClients.has(clientKey);
  }

  function isAmendmentOpen(clientKey, amKey) {
    if (!tariffExpandCaptured) return true;
    return expandedAmendments.has(`${clientKey}|${amKey}`);
  }

  function amendmentEditFormHtml(am) {
    const statusOpts = [
      ['draft', 'Черновик'],
      ['active', 'Действует'],
      ['superseded', 'Заменено'],
    ];
    let statusHtml = '<select data-am-field="status">';
    statusOpts.forEach(([v, l]) => {
      const sel = am.status === v ? ' selected' : '';
      statusHtml += `<option value="${v}"${sel}>${l}</option>`;
    });
    statusHtml += '</select>';
    return `
      <form class="ref-am-edit-form" data-amendment-id="${am.id}">
        <label><span>№ ДС</span><input data-am-field="number" value="${esc(am.number ?? '')}" required></label>
        <label><span>Действует с</span><input type="date" data-am-field="effective_from" value="${esc(am.effective_from ?? '')}"></label>
        <label><span>Действует до</span><input type="date" data-am-field="effective_to" value="${esc(am.effective_to ?? '')}"></label>
        <label><span>Статус</span>${statusHtml}</label>
        <div class="ref-group-actions">
          <button type="submit" class="btn-save-am">Сохранить ДС</button>
          <button type="button" class="btn-cancel-am">Отмена</button>
        </div>
      </form>`;
  }

  function displayCellHtml(fm, row) {
    if (!fm) return '';
    const f = fm.field;
    const val = row[f];
    if (f === 'report_role') return displayReportRole(fm, row);
    if (f === 'quantity_source') return displayQuantitySource(fm, row);
    if (f === 'billing_line_code') {
      const label = choiceLabel(fm, val);
      if (label) return esc(label);
      if (!val) return '<span class="muted">авто по наименованию</span>';
      return esc(val);
    }
    if (fm.lookup) return esc(lookupLabel(fm.lookup, val));
    if (fm.type === 'select') {
      const label = choiceLabel(fm, val);
      if (label) return esc(label);
      if (f === 'report_role' && val) return esc(ROLE_LABELS[val] || val);
      if (f === 'quantity_source' && val) return esc(QUANTITY_SOURCE_LABELS[val] || val);
    }
    if (fm.type === 'bool') return val ? 'да' : 'нет';
    if (f === 'is_custom') return val ? 'доп.' : 'основная';
    if (f === 'source_file_path' && val) return '<span class="muted">загружен</span>';
    return esc(val ?? '');
  }

  function renderTariffRowCells(cat, fields, row, rowEditing) {
    let html = '';
    fields.forEach((f) => {
      const fm = cat.field_meta.find((x) => x.field === f);
      if (rowEditing) {
        html += `<td>${fieldCellHtml(fm, row, false, true)}</td>`;
      } else {
        html += `<td class="display-cell">${displayCellHtml(fm, row)}</td>`;
      }
    });
    return html;
  }

  function newTariffRowDefaults(grp, amId, isCustom) {
    const am = grp.amendment;
    return {
      contract_id: grp.contract?.id,
      amendment_id: amId,
      is_custom: isCustom,
      valid_from: am?.effective_from || '',
      valid_to: am?.effective_to || '',
      name: '',
      unit_id: null,
      report_role: '',
      quantity_source: '',
      rate_ex_vat: null,
    };
  }

  function renderTariffSectionTable(cat, sectionRows, section, grp, amId, unlinked, clientKey) {
    const isCustom = section === 'extra';
    const title = section === 'main' ? 'Основные ставки (из ДС)' : 'Дополнительные (согласованы отдельно)';
    const pendingKey = amId ? `${amId}:${section}` : null;
    const hasPending = pendingKey && pendingNewRows.has(pendingKey);
    const canAdd = amId && !unlinked && !hasPending;
    const fields = tariffTableFields(cat, { includeBillingLine: Boolean(hasPending) });

    let html = '<div class="ref-tariff-section-block">';
    html += '<div class="ref-tariff-section-head">';
    html += `<h4 class="ref-tariff-section">${title}</h4>`;
    if (canAdd) {
      html += `<button type="button" class="btn-add-tariff-row" data-client-key="${esc(clientKey)}" data-amendment-id="${amId}" data-contract-id="${grp.contract.id}" data-section="${section}">+ Добавить строку</button>`;
    }
    html += '</div>';

    html += '<div class="table-wrap"><table class="data-table ref-table ref-tariff-table"><thead><tr>';
    html += '<th>№</th>';
    fields.forEach((f) => {
      const fm = cat.field_meta.find((x) => x.field === f);
      html += `<th>${esc(fm?.label || f)}</th>`;
    });
    html += '<th></th></tr></thead><tbody>';

    if (!sectionRows.length && !hasPending) {
      html += `<tr class="ref-empty-row"><td colspan="${fields.length + 2}" class="muted">Нет ставок</td></tr>`;
    }

    sectionRows.forEach((row, idx) => {
      const rowKey = String(row.id);
      const rowEditing = editingRows.has(rowKey);
      html += `<tr data-id="${row.id}" class="${rowEditing ? 'editing' : ''}">`;
      html += `<td class="row-num">${idx + 1}</td>`;
      html += renderTariffRowCells(cat, fields, row, rowEditing);
      html += '<td class="row-actions">';
      if (rowEditing) {
        html += '<button type="button" class="btn-save">Сохранить</button>';
        html += '<button type="button" class="btn-cancel">Отмена</button>';
      } else {
        html += '<button type="button" class="btn-edit">Изменить</button>';
        html += '<button type="button" class="btn-del">Удалить</button>';
      }
      html += '</td></tr>';
    });

    if (hasPending) {
      const draft = newTariffRowDefaults(grp, amId, isCustom);
      html += `<tr class="editing ref-new-row" data-new-key="${esc(pendingKey)}"
        data-amendment-id="${amId}" data-contract-id="${grp.contract.id}" data-is-custom="${isCustom ? '1' : '0'}">`;
      html += `<td class="row-num">+</td>`;
      html += renderTariffRowCells(cat, fields, draft, true);
      html += '<td class="row-actions">';
      html += '<button type="button" class="btn-save-new">Сохранить</button>';
      html += '<button type="button" class="btn-cancel-new">Отмена</button>';
      html += '</td></tr>';
    }

    html += '</tbody></table></div></div>';
    return html;
  }

  function renderStandardTable(prependHtml = '') {
    const cat = catMeta();
    const readOnly = cat.read_only;
    const fields = visibleFields(cat);

    let html = prependHtml;
    html += `<h2>${esc(cat.label || current)}</h2>`;
    if (cat.hint) html += `<p class="muted">${esc(cat.hint)}</p>`;
    if (readOnly) html += '<p class="muted">Только просмотр</p>';

    if (cat.field_meta?.some((f) => f.advanced)) {
      html += `<label class="ref-advanced-toggle"><input type="checkbox" id="toggle-advanced" ${showAdvanced ? 'checked' : ''}> Показать технические поля</label>`;
    }

    html += '<div class="table-wrap"><table class="data-table ref-table"><thead><tr>';
    html += '<th>№</th>';
    fields.forEach((f) => {
      const fm = cat.field_meta.find((x) => x.field === f);
      html += `<th>${esc(fm?.label || f)}</th>`;
    });
    if (!readOnly) html += '<th></th>';
    html += '</tr></thead><tbody>';

    items.forEach((row, idx) => {
      const rowKey = String(row.id);
      const rowEditing = editingRows.has(rowKey);
      html += `<tr data-id="${row.id}" class="${rowEditing ? 'editing' : ''}">`;
      html += `<td class="row-num">${idx + 1}</td>`;
      fields.forEach((f) => {
        const fm = cat.field_meta.find((x) => x.field === f);
        if (rowEditing) {
          html += `<td>${fieldCellHtml(fm, row, readOnly, true)}</td>`;
        } else {
          html += `<td class="display-cell">${displayCellHtml(fm, row)}</td>`;
        }
      });
      if (!readOnly) {
        html += '<td class="row-actions">';
        if (rowEditing) {
          html += '<button type="button" class="btn-save">Сохранить</button>';
          html += '<button type="button" class="btn-cancel">Отмена</button>';
        } else {
          html += '<button type="button" class="btn-edit">Изменить</button>';
          if (current !== 'product_types') {
            html += '<button type="button" class="btn-del">Удалить</button>';
          }
        }
        if (current === 'amendments') {
          html += `<button type="button" class="btn-upload" data-id="${row.id}">Файл ДС</button>`;
        }
        html += '</td>';
      }
      html += '</tr>';
    });
    html += '</tbody></table></div>';

    if (!readOnly) {
      html += renderAddForm(cat);
    }

    if (current === 'amendments') {
      html += renderAmendmentImport();
    }

    panelEl.innerHTML = html;
    bindTableEvents(cat);
  }

  function renderTariffGroups() {
    captureTariffExpandState();
    const cat = catMeta();
    const contractMap = Object.fromEntries((lookups.contracts || []).map((c) => [c.id, c]));
    const amMap = amendmentMap();

    const byClient = {};
    items.forEach((row) => {
      const c = contractMap[row.contract_id] || {
        id: row.contract_id,
        label: `№${row.contract_id}`,
        client_name: '',
        client_id: null,
      };
      const clientKey = c.client_id != null ? String(c.client_id) : `name:${c.client_name || c.label}`;
      const clientName = c.client_name || c.label.split(' — ')[0] || c.label;
      if (!byClient[clientKey]) {
        byClient[clientKey] = { name: clientName, clientId: c.client_id, amendments: {} };
      }
      const amKey = row.amendment_id || 'no_am';
      if (!byClient[clientKey].amendments[amKey]) {
        byClient[clientKey].amendments[amKey] = {
          amendment: amKey === 'no_am' ? null : amMap[Number(amKey)],
          contract: c,
          rows: [],
        };
      }
      byClient[clientKey].amendments[amKey].rows.push(row);
    });

    let html = `<h2>${esc(cat.label || 'Ставки')}</h2>`;
    if (cat.hint) html += `<p class="muted">${esc(cat.hint)}</p>`;
    html += `<label class="ref-advanced-toggle"><input type="checkbox" id="toggle-advanced" ${showAdvanced ? 'checked' : ''}> Показать технические поля</label>`;

    const clientKeys = Object.keys(byClient).sort((a, b) =>
      byClient[a].name.localeCompare(byClient[b].name, 'ru'),
    );

    if (!clientKeys.length) {
      html += '<p class="ref-no-ds-hint muted">Ставок пока нет. Сначала создайте ДС в разделе «Доп. соглашения».</p>';
    }

    clientKeys.forEach((clientKey) => {
      const clientGrp = byClient[clientKey];
      const clientTariffCount = Object.values(clientGrp.amendments).reduce((n, g) => n + g.rows.length, 0);
      const clientOpen = isClientOpen(clientKey) ? ' open' : '';

      html += `<details class="ref-group ref-client-group"${clientOpen} data-client-key="${esc(clientKey)}">`;
      html += '<summary class="ref-group-summary">';
      html += `<span class="ref-client-title">${esc(clientGrp.name)}</span>`;
      html += `<span class="muted ref-group-count">${clientTariffCount} ставок</span>`;
      if (clientGrp.clientId != null) {
        html += `<button type="button" class="btn-summary-action btn-del-client-rates" data-client-id="${clientGrp.clientId}">Удалить все</button>`;
      }
      html += '</summary>';

      const amKeys = Object.keys(clientGrp.amendments).sort((a, b) => {
        const aUnlinked = isUnlinkedAmendmentKey(a, amMap);
        const bUnlinked = isUnlinkedAmendmentKey(b, amMap);
        if (aUnlinked !== bUnlinked) return aUnlinked ? 1 : -1;
        const na = clientGrp.amendments[a].amendment?.number || '';
        const nb = clientGrp.amendments[b].amendment?.number || '';
        return String(na).localeCompare(String(nb), 'ru', { numeric: true });
      });

      const linkedAmKeys = amKeys.filter((k) => !isUnlinkedAmendmentKey(k, amMap));
      if (!linkedAmKeys.length && clientGrp.clientId != null && !amKeys.length) {
        html += '<p class="ref-no-ds-hint muted">Сначала создайте ДС в разделе «Доп. соглашения».</p>';
      }

      amKeys.forEach((amKey) => {
        const grp = clientGrp.amendments[amKey];
        const unlinked = isUnlinkedAmendmentKey(amKey, amMap);
        const amId = unlinked ? null : Number(amKey);
        const amOpen = isAmendmentOpen(clientKey, amKey) ? ' open' : '';

        html += `<details class="ref-group ref-am-group"${amOpen} data-amendment-key="${esc(amKey)}">`;
        html += '<summary class="ref-group-summary">';
        html += `<span class="ref-am-title">${esc(amendmentDisplayLabel(grp.amendment, unlinked))}</span>`;
        if (grp.contract) {
          const primary = contractPrimaryLabel(grp.contract);
          const secondary = contractSecondaryLabel(grp.contract);
          if (primary) {
            html += `<span class="muted ref-am-contract">${esc(primary)}</span>`;
          }
          if (secondary) {
            html += `<span class="muted ref-am-contract-sub">${esc(secondary)}</span>`;
          }
        }
        html += `<span class="muted ref-group-count">${grp.rows.length} ставок</span>`;
        if (amId) {
          html += `<button type="button" class="btn-summary-action btn-edit-am" data-amendment-id="${amId}">Изменить ДС</button>`;
          html += `<button type="button" class="btn-summary-action btn-del-am-rates" data-amendment-id="${amId}">Удалить все</button>`;
        } else if (grp.contract?.id) {
          html += `<button type="button" class="btn-summary-action btn-del-unlinked-rates" data-contract-id="${grp.contract.id}">Удалить группу</button>`;
        }
        html += '</summary>';

        if (unlinked) {
          html += '<p class="ref-unlinked-hint muted">Ставки без привязки к ДС. Добавление недоступно — удалите группу или привяжите к ДС вручную.</p>';
        }

        if (amId && editingAmendments.has(String(amId))) {
          html += amendmentEditFormHtml(grp.amendment);
        }

        if (unlinked) {
          html += renderTariffSectionTable(cat, grp.rows, 'main', grp, null, true, clientKey);
        } else {
          ['main', 'extra'].forEach((section) => {
            const sectionRows = grp.rows.filter((r) => (section === 'extra') === Boolean(r.is_custom));
            html += renderTariffSectionTable(cat, sectionRows, section, grp, amId, false, clientKey);
          });
        }

        html += '</details>';
      });

      if (!linkedAmKeys.length && clientGrp.clientId != null && amKeys.every((k) => isUnlinkedAmendmentKey(k, amMap))) {
        html += '<p class="ref-no-ds-hint muted">Сначала создайте ДС в разделе «Доп. соглашения».</p>';
      }

      html += '</details>';
    });

    panelEl.innerHTML = html;
    bindTableEvents(cat);
  }

  function renderAddForm(cat) {
    const fields = (cat.field_meta || []).filter((f) => !f.readonly);
    let html = '<h3>Добавить</h3><form id="add-form" class="add-form ref-add-form">';
    fields.forEach((fm) => {
      if (fm.advanced && !showAdvanced) return;
      html += `<label class="field-row"><span>${esc(fm.label)}</span>`;
      html += addFieldHtml(fm);
      html += '</label>';
    });
    html += '<button type="submit">Создать</button></form>';
    return html;
  }

  function addFieldHtml(fm) {
    const f = fm.field;
    if (fm.lookup) {
      const opts = lookupOptions(fm.lookup, {});
      let html = `<select name="${f}">`;
      html += '<option value="">—</option>';
      opts.forEach((o) => {
        html += `<option value="${o.id}">${esc(o.label)}</option>`;
      });
      html += '</select>';
      return html;
    }
    if (fm.type === 'bool') return `<input type="checkbox" name="${f}">`;
    if (fm.type === 'select' && fm.choices) {
      if (f === 'billing_line_code') {
        return billingLineSelectHtml(fm, '', false, { nameAttr: ` name="${f}"` });
      }
      let html = `<select name="${f}">`;
      fm.choices.forEach((c) => {
        html += `<option value="${esc(c.value)}">${esc(c.label)}</option>`;
      });
      html += '</select>';
      return html;
    }
    if (fm.type === 'date') return `<input type="date" name="${f}">`;
    if (f === 'rate_ex_vat') return `<input type="number" step="0.0001" name="${f}">`;
    return `<input type="text" name="${f}">`;
  }

  function renderAmendmentImport() {
    const opts = (lookups.contracts || []).map(
      (c) => `<option value="${c.id}">${esc(c.label)}</option>`,
    ).join('');
    return `
      <section class="ref-import-block">
        <h3>Импорт ДС из Word</h3>
        <p class="muted">Загрузите .docx — система создаст черновик ДС и загрузит ставки из таблицы тарифов.</p>
        <form id="import-am-form" class="ref-import-form" enctype="multipart/form-data">
          <label class="field-row"><span>Договор (осн.)</span>
            <select name="contract_id" required>${opts}</select>
          </label>
          <label class="field-row"><span>Файл .docx</span>
            <input type="file" name="file" accept=".docx" required>
          </label>
          <button type="submit" id="import-am-submit">Загрузить и создать черновик</button>
        </form>
      </section>`;
  }

  function stopSummaryToggle(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  function bindTableEvents(cat) {
    const adv = document.getElementById('toggle-advanced');
    if (adv) {
      adv.addEventListener('change', () => {
        showAdvanced = adv.checked;
        renderCurrent();
      });
    }

    panelEl.querySelectorAll('.btn-summary-action').forEach((btn) => {
      btn.addEventListener('click', stopSummaryToggle);
    });

    panelEl.querySelectorAll('.btn-edit').forEach((btn) => {
      btn.addEventListener('click', () => {
        editingRows.add(btn.closest('tr').dataset.id);
        renderCurrent();
      });
    });
    panelEl.querySelectorAll('.btn-cancel').forEach((btn) => {
      btn.addEventListener('click', () => {
        const tr = btn.closest('tr');
        if (tr?.dataset.id) editingRows.delete(tr.dataset.id);
        renderCurrent();
      });
    });
    panelEl.querySelectorAll('.btn-save').forEach((btn) => {
      btn.addEventListener('click', () => saveRow(btn.closest('tr')));
    });
    panelEl.querySelectorAll('.btn-del').forEach((btn) => {
      btn.addEventListener('click', () => deleteRow(btn.closest('tr')));
    });
    panelEl.querySelectorAll('.btn-upload').forEach((btn) => {
      btn.addEventListener('click', () => uploadAmendmentFile(btn.dataset.id));
    });

    panelEl.querySelectorAll('.btn-del-am-rates').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        stopSummaryToggle(e);
        deleteAmendmentRates(btn.dataset.amendmentId);
      });
    });
    panelEl.querySelectorAll('.btn-del-unlinked-rates').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        stopSummaryToggle(e);
        deleteUnlinkedRates(btn.dataset.contractId);
      });
    });
    panelEl.querySelectorAll('.btn-del-client-rates').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        stopSummaryToggle(e);
        deleteClientRates(btn.dataset.clientId);
      });
    });
    panelEl.querySelectorAll('.btn-edit-am').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        stopSummaryToggle(e);
        editingAmendments.add(String(btn.dataset.amendmentId));
        renderCurrent();
      });
    });
    panelEl.querySelectorAll('.btn-cancel-am').forEach((btn) => {
      btn.addEventListener('click', () => {
        const form = btn.closest('.ref-am-edit-form');
        if (form) editingAmendments.delete(String(form.dataset.amendmentId));
        renderCurrent();
      });
    });
    panelEl.querySelectorAll('.ref-am-edit-form').forEach((form) => {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        saveAmendmentForm(form);
      });
    });

    panelEl.querySelectorAll('.btn-add-tariff-row').forEach((btn) => {
      btn.addEventListener('click', () => {
        const key = `${btn.dataset.amendmentId}:${btn.dataset.section}`;
        pendingNewRows.add(key);
        if (btn.dataset.clientKey) expandedClients.add(btn.dataset.clientKey);
        if (btn.dataset.clientKey && btn.dataset.amendmentId) {
          expandedAmendments.add(`${btn.dataset.clientKey}|${btn.dataset.amendmentId}`);
        }
        tariffExpandCaptured = true;
        renderCurrent();
      });
    });
    panelEl.querySelectorAll('.btn-save-new').forEach((btn) => {
      btn.addEventListener('click', () => saveNewTariffRow(btn.closest('tr')));
    });
    panelEl.querySelectorAll('.btn-cancel-new').forEach((btn) => {
      btn.addEventListener('click', () => {
        const tr = btn.closest('tr');
        if (tr?.dataset.newKey) pendingNewRows.delete(tr.dataset.newKey);
        renderCurrent();
      });
    });

    const addForm = document.getElementById('add-form');
    if (addForm) addForm.addEventListener('submit', onAdd);

    const importForm = document.getElementById('import-am-form');
    if (importForm) importForm.addEventListener('submit', onImportAmendment);

    bindBillingLineCodeHandlers();
  }

  function readInputValue(el, fm) {
    if (el.type === 'checkbox') return el.checked;
    if (el.value === '') return null;
    if (fm?.lookup) return Number(el.value);
    if (fm?.field === 'rate_ex_vat') return el.value === '' ? null : Number(el.value);
    return el.value;
  }

  function normalizeStoredValue(fm, val) {
    if (fm?.type === 'bool') return Boolean(val);
    if (val == null || val === '') return null;
    if (fm?.lookup) return Number(val);
    if (fm?.field === 'rate_ex_vat') return Number(val);
    return String(val);
  }

  function fieldValuesEqual(fm, a, b) {
    return normalizeStoredValue(fm, a) === normalizeStoredValue(fm, b);
  }

  /** Только изменённые поля — пустые необязательные не затирают БД при правке другого поля. */
  function rowPayload(tr, originalRow) {
    const cat = catMeta();
    const payload = {};
    tr.querySelectorAll('[data-field]').forEach((el) => {
      const f = el.dataset.field;
      const fm = cat.field_meta?.find((x) => x.field === f);
      const newVal = readInputValue(el, fm);
      if (!originalRow) {
        if (el.type === 'checkbox') payload[f] = el.checked;
        else if (el.value !== '') payload[f] = el.value;
        return;
      }
      if (!fieldValuesEqual(fm, originalRow[f], newVal)) {
        payload[f] = newVal;
      }
    });
    return payload;
  }

  function slugifyCode(name) {
    const base = String(name || 'line')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9а-яё]+/gi, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 40);
    return base || `line_${Date.now()}`;
  }

  async function saveNewTariffRow(tr) {
    const payload = rowPayload(tr);
    payload.contract_id = Number(tr.dataset.contractId);
    payload.amendment_id = Number(tr.dataset.amendmentId);
    payload.is_custom = tr.dataset.isCustom === '1';
    if (!payload.amendment_id) {
      setStatus('Нельзя создать ставку без ДС. Сначала создайте доп. соглашение.', true);
      return;
    }
    if (!payload.name?.trim()) {
      setStatus('Укажите наименование ставки.', true);
      return;
    }
    if (!payload.valid_from) {
      setStatus('Укажите дату начала действия ставки.', true);
      return;
    }
    try {
      await api('/api/reference/tariff_rules', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      if (tr.dataset.newKey) pendingNewRows.delete(tr.dataset.newKey);
      setStatus('Ставка создана.');
      await loadItems();
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function saveRow(tr) {
    const id = tr.dataset.id;
    if (!id) return;
    const originalRow = items.find((r) => String(r.id) === String(id));
    const payload = rowPayload(tr, originalRow);
    if (!Object.keys(payload).length) {
      editingRows.delete(id);
      setStatus('Нет изменений.');
      renderCurrent();
      return;
    }
    try {
      await api(`/api/reference/${current}/${id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      });
      editingRows.delete(id);
      setStatus('Сохранено.');
      if (current === 'contracts') await loadLookups(true);
      await loadItems();
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function deleteUnlinkedRates(contractId) {
    const cid = Number(contractId);
    if (!cid) {
      setStatus('Не указан договор для удаления группы.', true);
      return;
    }
    if (!confirm('Удалить все ставки без привязки к ДС по этому договору?')) return;
    try {
      const data = await api(
        `/api/reference/tariff_rules/bulk?contract_id=${cid}&unlinked=1`,
        { method: 'DELETE' },
      );
      setStatus(`Удалено ставок: ${data.deleted ?? 0}.`);
      await loadItems();
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function deleteAmendmentRates(amendmentId) {
    const aid = Number(amendmentId);
    if (!aid) {
      setStatus('Не указано ДС для удаления ставок.', true);
      return;
    }
    if (!confirm('Удалить все ставки этого ДС? Договор и само ДС не удаляются.')) return;
    try {
      const data = await api(`/api/reference/tariff_rules/bulk?amendment_id=${aid}`, { method: 'DELETE' });
      setStatus(`Удалено ставок: ${data.deleted ?? 0}.`);
      await loadItems();
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function deleteClientRates(clientId) {
    const clid = Number(clientId);
    if (!clid) {
      setStatus('Не указан клиент для удаления ставок.', true);
      return;
    }
    if (!confirm('Удалить все ставки клиента по всем договорам и ДС?')) return;
    try {
      const data = await api(`/api/reference/tariff_rules/bulk?client_id=${clid}`, { method: 'DELETE' });
      setStatus(`Удалено ставок: ${data.deleted ?? 0}.`);
      await loadItems();
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function saveAmendmentForm(form) {
    const id = form.dataset.amendmentId;
    const original = (lookups.amendments || []).find((a) => String(a.id) === String(id)) || {};
    const payload = {};
    form.querySelectorAll('[data-am-field]').forEach((el) => {
      const f = el.dataset.amField;
      const newVal = el.type === 'checkbox' ? el.checked : (el.value === '' ? null : el.value);
      const oldVal = el.type === 'checkbox' ? Boolean(original[f]) : (original[f] ?? null);
      if (newVal !== oldVal && !(newVal == null && (oldVal == null || oldVal === ''))) {
        payload[f] = newVal;
      }
    });
    if (!Object.keys(payload).length) {
      editingAmendments.delete(String(id));
      setStatus('Нет изменений.');
      renderCurrent();
      return;
    }
    try {
      await api(`/api/reference/amendments/${id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      });
      editingAmendments.delete(String(id));
      setStatus('ДС сохранено.');
      await loadLookups(true);
      await loadItems();
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function deleteRow(tr) {
    const id = tr.dataset.id;
    if (!confirm(`Удалить ставку №${tr.querySelector('.row-num')?.textContent || id}?`)) return;
    try {
      await api(`/api/reference/${current}/${id}`, { method: 'DELETE' });
      editingRows.delete(id);
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

  async function uploadAmendmentFile(id) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.docx';
    input.addEventListener('change', async () => {
      if (!input.files?.length) return;
      const fd = new FormData();
      fd.append('file', input.files[0]);
      try {
        const r = await fetch(`/api/reference/amendments/${id}/upload`, {
          method: 'POST',
          credentials: 'same-origin',
          body: fd,
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.message || data.error);
        const n = data.tariffs_created ?? 0;
        setStatus(data.message || `Файл загружен. Ставок: ${n}.`);
        await loadLookups(true);
        await loadItems();
      } catch (e) {
        setStatus(e.message, true);
      }
    });
    input.click();
  }

  async function onImportAmendment(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('#import-am-submit') || form.querySelector('[type="submit"]');
    const fd = new FormData(form);
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Импорт…';
    }
    setStatus('Импорт документа…');
    try {
      const r = await fetch('/api/reference/amendments/import', {
        method: 'POST',
        credentials: 'same-origin',
        body: fd,
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.message || data.error);
      const n = data.tariffs_created ?? 0;
      setStatus(data.message || `Черновик создан. Ставок: ${n}.`);
      form.reset();
      await loadLookups(true);
      await loadItems();
      if (n > 0 && meta.some((c) => c.code === 'tariff_rules')) {
        await selectCatalog('tariff_rules');
      }
    } catch (err) {
      setStatus(err.message, true);
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Загрузить и создать черновик';
      }
    }
  }

  function fmtDateShort(d) {
    if (!d) return '—';
    const s = String(d).slice(0, 10);
    const [y, m, day] = s.split('-');
    return day && m && y ? `${day}.${m}.${y}` : s;
  }

  async function amendmentsOverviewHtml() {
    try {
      const data = await api('/api/reference/amendments-overview');
      if (!data.length) {
        return '<section class="ref-amd-overview"><p class="muted">Нет допсоглашений. Создайте клиента и ДС ниже.</p></section>';
      }
      let html = '<section class="ref-amd-overview"><h3>Обзор ДС по складам</h3>';
      data.forEach((wh) => {
        html += `<details class="ref-amd-wh" open><summary><strong>${esc(wh.warehouse_name)}</strong></summary>`;
        (wh.clients || []).forEach((cl) => {
          html += `<div class="ref-amd-client"><h4>${esc(cl.client_name)}`;
          html += ` <span class="muted">· ${esc(cl.service_name || '')} · дог. ${esc(cl.contract_number)}</span></h4>`;
          (cl.amendments || []).forEach((am) => {
            const lifecycle = am.lifecycle === 'active' ? 'Действующее' : 'Завершённое';
            html += `<details class="ref-amd-card"><summary>${esc(am.number)}`;
            html += ` <span class="muted">— ${lifecycle}</span>`;
            if (am.expiring_soon) html += ' <span class="ref-amd-warn">≤ 1 мес.</span>';
            html += ` <span class="muted">· ${fmtDateShort(am.effective_from)} — `;
            html += `${am.effective_to ? fmtDateShort(am.effective_to) : 'бессрочно'}</span></summary>`;
            if (am.tariffs?.length) {
              html += '<table class="data-table ref-table"><thead><tr>';
              html += '<th>Наименование</th><th>Ед.</th><th>Без НДС</th><th>С НДС</th><th>По</th></tr></thead><tbody>';
              am.tariffs.forEach((t) => {
                html += '<tr>';
                html += `<td>${esc(t.name)}</td><td>${esc(t.unit_code || '—')}</td>`;
                html += `<td>${t.rate_ex_vat != null ? fmtMoney(t.rate_ex_vat) : '—'}</td>`;
                html += `<td>${t.rate_inc_vat != null ? fmtMoney(t.rate_inc_vat) : '—'}</td>`;
                html += `<td>${t.valid_to ? fmtDateShort(t.valid_to) : '—'}</td></tr>`;
              });
              html += '</tbody></table>';
            } else {
              html += '<p class="muted">Ставок нет</p>';
            }
            html += '</details>';
          });
          html += '</div>';
        });
        html += '</details>';
      });
      html += '</section><hr class="ref-section-divider">';
      return html;
    } catch (e) {
      return `<p class="muted">Обзор ДС недоступен: ${esc(e.message)}</p>`;
    }
  }

  function renderCurrent() {
    const cat = catMeta();
    if (cat.custom_ui && current === 'warehouse_staff') {
      renderWarehouseStaff();
      return;
    }
    if (cat.grouped) {
      renderTariffGroups();
      return;
    }
    if (current === 'amendments') {
      panelEl.innerHTML = '<p class="muted">Загрузка обзора…</p>';
      amendmentsOverviewHtml().then((overview) => {
        renderStandardTable(overview);
      });
      return;
    }
    renderStandardTable();
  }

  function todayIso() {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function fmtMoney(v) {
    return new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(v) || 0);
  }

  async function renderWarehouseStaff() {
    const cat = catMeta();
    setHintVisible(Boolean(cat.hint));
    if (hintEl && cat.hint) hintEl.textContent = cat.hint;
    const data = await api('/api/reference/warehouse-staff');
    items = data.items || [];
    const whMap = Object.fromEntries((lookups.warehouses || []).map((w) => [w.id, w.label]));
    const fotTotal = items.reduce((s, p) => s + Number(p.monthly_total || 0), 0);
    const whOpts = (lookups.warehouses || []).map((w) => `<option value="${w.id}">${esc(w.label)}</option>`).join('');

    panelEl.innerHTML = `
      <p class="muted">Суммарный ФОТ: <strong>${fmtMoney(fotTotal)}</strong> ₽/мес (текущий)</p>
      <table class="data-table ref-table">
        <thead><tr>
          <th>Склад</th><th>Должность</th><th>Оклад, ₽/мес</th><th>Кол-во</th><th>ФОТ, ₽/мес</th>
          <th>Действует с</th><th>Порядок</th><th></th>
        </tr></thead>
        <tbody id="wh-staff-tbody">
          ${items.length ? items.map((p) => `
            <tr class="wh-staff-row" data-id="${p.id}">
              <td><span class="catalog-static">${esc(whMap[p.warehouse_id] || p.warehouse_id)}</span></td>
              <td><input data-f="name" value="${esc(p.name)}"></td>
              <td><input data-f="monthly_rate" type="number" min="0" step="0.01" value="${p.monthly_rate}"></td>
              <td><input data-f="headcount" type="number" min="1" step="1" value="${p.headcount}"></td>
              <td class="wh-staff-total">${fmtMoney(p.monthly_total)}</td>
              <td><input data-f="effective_from" type="date" value="${todayIso()}" title="При изменении оклада или численности"></td>
              <td><input data-f="sort_order" type="number" value="${p.sort_order ?? 100}"></td>
              <td><button type="button" class="btn btn-danger btn-sm wh-staff-del">Удалить</button></td>
            </tr>`).join('') : '<tr><td colspan="8" class="muted">Нет позиций</td></tr>'}
        </tbody>
      </table>
      <div class="ref-actions" style="margin-top:0.75rem">
        <button type="button" class="btn" id="wh-staff-add">Добавить позицию</button>
        <button type="button" class="btn btn-primary" id="wh-staff-save">Сохранить</button>
      </div>`;

    const tbody = document.getElementById('wh-staff-tbody');
    const recalc = (row) => {
      const rate = Number(row.querySelector('[data-f="monthly_rate"]')?.value || 0);
      const hc = Number(row.querySelector('[data-f="headcount"]')?.value || 0);
      const cell = row.querySelector('.wh-staff-total');
      if (cell) cell.textContent = fmtMoney(rate * hc);
    };
    panelEl.querySelectorAll('.wh-staff-row').forEach((row) => {
      row.querySelectorAll('[data-f="monthly_rate"], [data-f="headcount"]').forEach((inp) => {
        inp.addEventListener('input', () => recalc(row));
      });
      row.querySelector('.wh-staff-del')?.addEventListener('click', async () => {
        if (!confirm('Удалить позицию?')) return;
        await api(`/api/reference/warehouse-staff/${row.dataset.id}`, { method: 'DELETE' });
        setStatus('Удалено');
        await renderWarehouseStaff();
      });
    });

    document.getElementById('wh-staff-add')?.addEventListener('click', () => {
      tbody.querySelector('.muted')?.closest('tr')?.remove();
      const tr = document.createElement('tr');
      tr.className = 'wh-staff-row wh-staff-new';
      tr.innerHTML = `
        <td><select data-f="warehouse_id">${whOpts}</select></td>
        <td><input data-f="name" placeholder="Оператор" required></td>
        <td><input data-f="monthly_rate" type="number" min="0" step="0.01"></td>
        <td><input data-f="headcount" type="number" min="1" step="1" value="1"></td>
        <td class="wh-staff-total">0</td>
        <td><input data-f="effective_from" type="date" value="${todayIso()}"></td>
        <td><input data-f="sort_order" type="number" value="100"></td>
        <td></td>`;
      tbody.appendChild(tr);
      tr.querySelectorAll('[data-f="monthly_rate"], [data-f="headcount"]').forEach((inp) => {
        inp.addEventListener('input', () => recalc(tr));
      });
    });

    document.getElementById('wh-staff-save')?.addEventListener('click', async () => {
      setStatus('Сохранение…');
      try {
        for (const row of panelEl.querySelectorAll('.wh-staff-new')) {
          const get = (f) => row.querySelector(`[data-f="${f}"]`)?.value;
          await api('/api/reference/warehouse-staff', {
            method: 'POST',
            body: JSON.stringify({
              warehouse_id: Number(get('warehouse_id')),
              name: get('name')?.trim(),
              monthly_rate: get('monthly_rate'),
              headcount: get('headcount'),
              sort_order: get('sort_order'),
              effective_from: get('effective_from'),
            }),
          });
        }
        for (const row of panelEl.querySelectorAll('.wh-staff-row:not(.wh-staff-new)')) {
          const get = (f) => row.querySelector(`[data-f="${f}"]`)?.value;
          await api(`/api/reference/warehouse-staff/${row.dataset.id}`, {
            method: 'PUT',
            body: JSON.stringify({
              name: get('name')?.trim(),
              monthly_rate: get('monthly_rate'),
              headcount: get('headcount'),
              sort_order: get('sort_order'),
              effective_from: get('effective_from'),
            }),
          });
        }
        setStatus('Сохранено');
        await renderWarehouseStaff();
      } catch (e) {
        setStatus(e.message, true);
      }
    });
  }

  function renderNav() {
    navEl.innerHTML = '';
    meta.forEach((c) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = c.code === current ? 'active' : '';
      btn.textContent = c.label || c.code;
      btn.addEventListener('click', () => selectCatalog(c.code));
      navEl.appendChild(btn);
    });
  }

  async function loadLookups(force = false) {
    if (!force && lookups.clients?.length) return;
    try {
      const data = await api('/api/reference/meta');
      if (data.lookups) {
        lookups = data.lookups;
        return;
      }
    } catch { /* meta недоступен */ }
    lookups = await api('/api/reference/lookups?all=1');
  }

  async function loadItems() {
    if (current === 'warehouse_staff') {
      renderCurrent();
      return;
    }
    const data = await api(`/api/reference/${current}`);
    items = data.items || [];
    renderCurrent();
  }

  async function selectCatalog(code) {
    current = code;
    editingRows.clear();
    editingAmendments.clear();
    pendingNewRows.clear();
    expandedClients.clear();
    expandedAmendments.clear();
    tariffExpandCaptured = false;
    showAdvanced = false;
    setHintVisible(false);
    renderNav();
    setStatus('Загрузка…');
    try {
      await loadLookups(true);
      await loadItems();
      const cat = catMeta();
      setStatus(`${cat.label || code}: ${items.length} записей`);
    } catch (e) {
      setStatus(e.message, true);
      panelEl.innerHTML = '';
      setHintVisible(true);
    }
  }

  async function init() {
    try {
      const data = await api('/api/reference/meta');
      meta = data.catalogs || [];
      lookups = data.lookups || {};
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
