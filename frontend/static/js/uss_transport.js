/** Ежесменный отчёт транспортной логистики */
(async function initTransportShift() {
  const statusEl = document.getElementById('status');
  const toolbarEl = document.getElementById('toolbar');
  const contentEl = document.getElementById('content');
  const role = 'transport_logistics';
  let vehicleTypes = [];

  const COL_CLASS = {
    tractor_plate: 'col-plate',
    trailer_plate: 'col-plate',
    operation_type_code: 'col-op',
    waybill_numbers: 'col-waybill',
    mx_numbers: 'col-mx',
    vehicle_type_id: 'col-type',
    seal_number: 'col-seal',
    torg2_number: 'col-torg2',
    volume_document_m3: 'col-vol',
    handling_type_code: 'col-handling',
    extra_handling_m3: 'col-vol',
    registered_at: 'col-time',
    departed_at: 'col-time',
    extra_document_set_qty: 'col-qty',
  };

  const REQUIRED_HINT = 'Для завершения обработки: тягач, операция, прибытие, убытие (прицеп — по необходимости).';

  function setStatus(msg, isError) {
    statusEl.textContent = msg;
    statusEl.className = isError ? 'status error' : 'status';
  }

  async function syncSecurity(warehouseId, date) {
    setStatus('Синхронизация с охраной…');
    try {
      const data = await UssApi.json('/api/uss/transport/sync-security', {
        method: 'POST',
        body: JSON.stringify({ warehouse_id: Number(warehouseId), date }),
      });
      let msg = `Охрана: +${data.synced} ТС (${data.source || '—'})`;
      if (data.raw_rows != null) msg += `, заявок в портале: ${data.raw_rows}`;
      if (data.message) msg += `. ${data.message}`;
      if (data.warnings?.length) msg += ` ${data.warnings.join(' ')}`;
      setStatus(msg, Boolean(data.synced === 0 && !data.message?.includes('демо')));
      load();
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  function renderSecurityHint(toolbarHost, security, visitPlace) {
    const existing = toolbarHost.querySelector('.security-status-hint');
    if (existing) existing.remove();
    if (!security) return;
    const hint = document.createElement('span');
    hint.className = 'security-status-hint muted';
    hint.id = 'transport-security-status';
    const place = visitPlace ? `, место визита: «${visitPlace}»` : ', место визита СБ не задано';
    hint.textContent = `Охрана: ${security.label || security.source}${place}`;
    hint.title = security.stub
      ? 'Включена заглушка SECURITY_PORTAL_STUB — демо-заявки'
      : security.source === 'local_cache'
        ? 'Тест: портал security.bsh-ru.ru, при отсутствии SSO — локальный кэш'
        : 'Нажмите «С охраны» для загрузки ТС из портала';
    toolbarHost.querySelector('.toolbar')?.appendChild(hint);
  }

  function fieldValue(vehicle, fieldDef) {
    if (fieldDef.tariff_input || (fieldDef.field && fieldDef.field.startsWith('rq_'))) {
      const code = fieldDef.billing_line_code || fieldDef.field.slice(3);
      return vehicle.report_quantities?.[code];
    }
    return vehicle[fieldDef.field];
  }

  function collectPayload(vehicle, fields, inputs, warehouseId, opDate) {
    const payload = {
      warehouse_id: warehouseId,
      contract_id: vehicle.contract_id,
      operation_date: opDate,
    };
    if (vehicle.id) payload.id = vehicle.id;
    const reportQuantities = { ...(vehicle.report_quantities || {}) };
    fields.forEach((f) => {
      if (f.input_type === 'waybill_column' || f.input_type === 'mx_column') {
        if (f.input_type === 'waybill_column') {
          payload.waybills = inputs.waybills?.collect?.() || [];
        }
        return;
      }
      if (!inputs[f.field]) return;
      const v = inputs[f.field].value;
      if (f.tariff_input || (f.field && f.field.startsWith('rq_'))) {
        const code = f.billing_line_code || f.field.slice(3);
        if (v === '') delete reportQuantities[code];
        else reportQuantities[code] = Number(v);
        return;
      }
      payload[f.field] = v === '' ? null : v;
    });
    if (Object.keys(reportQuantities).length) payload.report_quantities = reportQuantities;
    return payload;
  }

  function renderProcessedCell(tr, vehicle) {
    const td = document.createElement('td');
    td.className = 'col-processed';
    if (vehicle.arrival_status === 'no_show') {
      td.innerHTML = '<span class="vehicle-status-badge vehicle-status-badge--no-show">Не прибыл</span>';
    } else if (vehicle.is_complete && vehicle.processed_by_name) {
      const when = vehicle.processed_at ? vehicle.processed_at.replace('T', ' ').slice(0, 16) : '';
      td.innerHTML = `<span class="vehicle-processed-badge" title="${when}">${vehicle.processed_by_name}</span>`;
    } else if (vehicle.missing_fields?.length) {
      td.innerHTML = '<span class="muted vehicle-draft-badge">в работе</span>';
    }
    tr.appendChild(td);
  }

  function vehicleRow(vehicle, fields, warehouseId, opDate, isNew, periodLocked) {
    const tr = document.createElement('tr');
    tr.dataset.vehicleId = vehicle.id || '';
    if (vehicle.is_complete) tr.classList.add('vehicle-row-complete');
    if (vehicle.arrival_status === 'no_show') tr.classList.add('vehicle-row-no-show');
    if (vehicle.source === 'security') tr.classList.add('vehicle-from-security');

    const inputs = {};
    let waybillsEditor = null;
    let editing = isNew;

    fields.forEach((f) => {
      const td = document.createElement('td');
      td.className = COL_CLASS[f.field] || '';
      if (f.input_type === 'waybill_column' || f.input_type === 'mx_column') {
        if (!waybillsEditor) {
          waybillsEditor = UssApi.createWaybillsEditor(
            vehicle.waybills,
            vehicle.operation_type_code || 'inbound',
            false,
          );
          inputs.waybills = waybillsEditor;
        }
        td.appendChild(f.input_type === 'waybill_column' ? waybillsEditor.waybillCol : waybillsEditor.mxCol);
      } else {
        const inp = UssApi.renderSchemaField(f, fieldValue(vehicle, f), { vehicleTypes, disabled: true });
        inputs[f.field] = inp;
        td.appendChild(inp);
        if (f.field === 'operation_type_code') {
          inp.addEventListener('change', () => waybillsEditor?.updateOpType(inp.value));
        }
        if (f.field === 'tractor_plate' && vehicle.source === 'security') {
          const badge = document.createElement('span');
          badge.className = 'security-badge';
          badge.textContent = 'охрана';
          badge.title = 'Строка загружена из портала охраны';
          td.appendChild(badge);
        }
      }
      tr.appendChild(td);
    });

    renderProcessedCell(tr, vehicle);

    const tdBtn = document.createElement('td');
    tdBtn.className = 'col-actions vehicle-row-actions';

    const btnEdit = document.createElement('button');
    btnEdit.type = 'button';
    btnEdit.className = 'ref-btn ref-btn--ghost btn-row-edit';
    btnEdit.textContent = 'Изменить';

    const btnSave = document.createElement('button');
    btnSave.type = 'button';
    btnSave.className = 'ref-btn ref-btn--primary btn-row-save';
    btnSave.textContent = isNew ? 'Создать' : 'Сохранить';
    btnSave.hidden = !isNew;

    const btnCancel = document.createElement('button');
    btnCancel.type = 'button';
    btnCancel.className = 'ref-btn btn-row-cancel';
    btnCancel.textContent = 'Отмена';
    btnCancel.hidden = !isNew;

    const btnNoShow = document.createElement('button');
    btnNoShow.type = 'button';
    btnNoShow.className = 'ref-btn btn-row-no-show';
    btnNoShow.textContent = 'Не прибыл';
    btnNoShow.title = 'Заявка была, ТС не приехало';
    btnNoShow.hidden = isNew || !vehicle.id || vehicle.arrival_status === 'no_show';

    const btnHistory = document.createElement('button');
    btnHistory.type = 'button';
    btnHistory.className = 'ref-btn ref-btn--ghost btn-row-history';
    btnHistory.textContent = 'История';
    btnHistory.hidden = isNew || !vehicle.id;

    function setEditing(on) {
      editing = on;
      UssApi.setRowFieldsEditable(tr, on);
      waybillsEditor?.setEditable?.(on);
      btnEdit.hidden = on || periodLocked;
      btnSave.hidden = !on;
      btnCancel.hidden = !on;
      btnNoShow.hidden = on || isNew || !vehicle.id || vehicle.arrival_status === 'no_show' || periodLocked;
      btnHistory.hidden = isNew || !vehicle.id;
      tr.classList.toggle('vehicle-row-editing', on);
    }

    setEditing(isNew);

    btnEdit.addEventListener('click', () => setEditing(true));
    btnCancel.addEventListener('click', () => {
      if (isNew) tr.remove();
      else load();
    });

    btnSave.addEventListener('click', async () => {
      try {
        const payload = collectPayload(vehicle, fields, inputs, warehouseId, opDate);
        await UssApi.json('/api/uss/transport/vehicles', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        setStatus(isNew ? 'Строка создана.' : 'Сохранено.');
        load();
      } catch (e) {
        setStatus(e.message, true);
      }
    });

    btnNoShow.addEventListener('click', async () => {
      if (!window.confirm('Отметить ТС как «не прибыл»?')) return;
      try {
        await UssApi.json(`/api/uss/transport/vehicles/${vehicle.id}/no-show`, { method: 'POST', body: '{}' });
        setStatus('Отмечено: не прибыл.');
        load();
      } catch (e) {
        setStatus(e.message, true);
      }
    });

    btnHistory.addEventListener('click', async () => {
      try {
        await UssApi.showVehicleAuditDialog(vehicle.id);
      } catch (e) {
        setStatus(e.message, true);
      }
    });

    if (periodLocked) {
      btnEdit.disabled = true;
      btnNoShow.disabled = true;
    }

    tdBtn.append(btnEdit, btnSave, btnCancel, btnNoShow, btnHistory);
    tr.appendChild(tdBtn);
    return tr;
  }

  function renderVehicles(container, vehicles, contractId, warehouseId, opDate, schema, periodLocked) {
    const fields = schema.vehicle_fixed_fields || [];
    container.innerHTML = '';
    container.className = 'vehicles-section';

    const hint = document.createElement('p');
    hint.className = 'muted uss-shift-field-hint';
    hint.textContent = REQUIRED_HINT;
    container.appendChild(hint);

    const wrap = document.createElement('div');
    wrap.className = 'transport-table-wrap';
    const table = document.createElement('table');
    table.className = 'data-table transport-wide-table';

    const thead = document.createElement('thead');
    const hr = document.createElement('tr');
    fields.forEach((f) => {
      const th = document.createElement('th');
      th.textContent = f.label;
      th.className = COL_CLASS[f.field] || '';
      th.title = f.label;
      hr.appendChild(th);
    });
    const thProc = document.createElement('th');
    thProc.textContent = 'Обработал';
    thProc.className = 'col-processed';
    hr.appendChild(thProc);
    const thAct = document.createElement('th');
    thAct.className = 'col-actions';
    hr.appendChild(thAct);
    thead.appendChild(hr);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    vehicles.forEach((v) => {
      tbody.appendChild(vehicleRow(v, fields, warehouseId, opDate, false, periodLocked));
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
    container.appendChild(wrap);

    if (!periodLocked) {
      const addBtn = document.createElement('button');
      addBtn.type = 'button';
      addBtn.className = 'ref-btn';
      addBtn.textContent = '+ Добавить ТС';
      addBtn.addEventListener('click', () => {
        const empty = { contract_id: contractId, report_quantities: {}, waybills: [] };
        tbody.appendChild(vehicleRow(empty, fields, warehouseId, opDate, true, false));
      });
      container.appendChild(addBtn);
    }
  }

  async function load() {
    const q = UssApi.qs();
    const date = q.get('date') || UssApi.today();
    let warehouseId = q.get('warehouse_id');
    setStatus('Загрузка…');
    try {
      const ctx = await UssApi.json(
        `/api/uss/context?role=${role}&date=${date}${warehouseId ? `&warehouse_id=${warehouseId}` : ''}`,
      );
      warehouseId = String(ctx.warehouse_id);
      UssApi.setQs({ warehouse_id: warehouseId, date: ctx.date });

      UssApi.renderToolbar(toolbarEl, {
        warehouses: ctx.warehouses,
        warehouseId,
        date: ctx.date,
        role,
        minDate: ctx.min_date,
        maxDate: ctx.max_date,
        onChange: (p) => { UssApi.setQs(p); load(); },
      });

      const syncBtn = document.createElement('button');
      syncBtn.type = 'button';
      syncBtn.id = 'btn-sync-security';
      syncBtn.textContent = 'С охраны';
      syncBtn.className = 'toolbar-btn btn-primary-sm';
      syncBtn.title = 'Загрузить ТС из портала охраны';
      syncBtn.addEventListener('click', () => syncSecurity(warehouseId, ctx.date));
      toolbarEl.querySelector('.toolbar')?.appendChild(syncBtn);
      renderSecurityHint(toolbarEl, ctx.security, ctx.security_visit_place);

      const data = await UssApi.json(
        `/api/uss/transport/shift?warehouse_id=${warehouseId}&date=${ctx.date}`,
      );
      vehicleTypes = data.vehicle_types || [];
      renderSecurityHint(toolbarEl, data.security, data.security_visit_place);
      contentEl.innerHTML = '';

      if (!data.contracts?.length) {
        contentEl.innerHTML = '<p class="muted">На выбранную дату нет договоров с действующим ДС. Выберите другую дату или проверьте доп. соглашения.</p>';
        setStatus(`Склад ${warehouseId}, ${data.operation_date} — нет договоров на дату`);
        return;
      }

      const monthLabel = data.operation_date?.slice(0, 7);
      const clientGroups = UssApi.groupContractsByClient(data.contracts);

      function clientVehicleCount(group) {
        const ids = new Set(group.contracts.map((c) => String(c.contract_id || c.id)));
        return (data.vehicles || []).filter((v) => ids.has(String(v.contract_id))).length;
      }

      function renderContractBlock(c) {
        const block = document.createElement('section');
        block.className = 'contract-block';
        const blockKey = UssApi.contractBlockKey(c);
        const cid = String(c.contract_id || c.id);
        const schema = data.schemas?.[blockKey] || data.schemas?.[cid] || {};
        const totals = UssApi.totalsMap(data.daily_totals?.[cid]);
        const vehicles = (data.vehicles || []).filter((v) => String(v.contract_id) === cid);
        const periodInputs = schema.period_inputs || [];
        const periodLocked = UssApi.applyContractPeriodLock(block, data.period_locks?.[cid], monthLabel);

        UssApi.renderContractHeader(block, c);
        UssApi.renderContractDateHint(block, c.date_hint);

        const tabsHost = document.createElement('div');
        block.appendChild(tabsHost);

        const tabs = [{
          label: 'ТС',
          render: (panel) => {
            renderVehicles(panel, vehicles, c.id, data.warehouse_id, data.operation_date, schema, periodLocked);
          },
        }];

        if (periodInputs.length) {
          tabs.push({
            label: 'Дополнительный',
            render: (panel) => {
              UssApi.renderDailyReportForm(panel, {
                schema: { period_inputs: periodInputs },
                totals,
                readOnly: periodLocked,
                onPeriodSave: async (entries) => {
                  try {
                    await UssApi.json('/api/uss/transport/daily', {
                      method: 'POST',
                      body: JSON.stringify({
                        warehouse_id: data.warehouse_id,
                        contract_id: c.id,
                        report_date: data.operation_date,
                        entries,
                      }),
                    });
                    setStatus('Дополнительные поля сохранены.');
                    load();
                  } catch (e) {
                    setStatus(e.message, true);
                  }
                },
              });
            },
          });
        }

        UssApi.renderContractTabs(tabsHost, tabs);
        return block;
      }

      if (clientGroups.length <= 1) {
        (clientGroups[0]?.contracts || data.contracts || []).forEach((c) => {
          contentEl.appendChild(renderContractBlock(c));
        });
      } else {
        const clientTabsHost = document.createElement('div');
        clientTabsHost.className = 'transport-client-tabs';
        contentEl.appendChild(clientTabsHost);
        UssApi.renderContractTabs(clientTabsHost, clientGroups.map((g) => ({
          label: `${g.client_name} (${clientVehicleCount(g)})`,
          render: (panel) => {
            const wrap = document.createElement('div');
            wrap.className = 'transport-client-panel';
            g.contracts.forEach((c) => wrap.appendChild(renderContractBlock(c)));
            panel.appendChild(wrap);
          },
        })));
      }

      const sec = data.security?.label || (data.security?.source === 'demo' ? 'демо-охрана' : '');
      const placeWarn = !data.security_visit_place ? ' — задайте «Место визита СБ» у склада' : '';
      setStatus(`Склад ${warehouseId}, ${data.operation_date}${sec ? ` (${sec})` : ''}${placeWarn}`);
    } catch (e) {
      setStatus(e.message === 'unauthorized' ? 'Войдите в систему' : e.message, true);
    }
  }

  await load();
})();
