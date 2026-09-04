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

  function readNav() {
    const q = UssApi.qs();
    return {
      clientId: q.get('client_id') || '',
      contractId: q.get('contract_id') || '',
      panel: q.get('panel') || 'vehicles',
    };
  }

  function writeNav(partial, base = {}) {
    const q = UssApi.qs();
    const next = {
      warehouse_id: base.warehouse_id ?? q.get('warehouse_id') ?? '',
      date: base.date ?? q.get('date') ?? '',
      client_id: partial.clientId ?? readNav().clientId,
      contract_id: partial.contractId ?? readNav().contractId,
      panel: partial.panel ?? readNav().panel,
    };
    Object.keys(next).forEach((k) => {
      if (!next[k]) delete next[k];
    });
    UssApi.setQs(next);
  }

  function reload(nav = {}) {
    writeNav(nav);
    load();
  }

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
      reload();
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

  function vehicleRow(vehicle, fields, warehouseId, opDate, isNew, periodLocked, nav) {
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

    const mainActions = document.createElement('div');
    mainActions.className = 'vehicle-row-actions-main';

    const extraActions = document.createElement('div');
    extraActions.className = 'vehicle-row-actions-extra';

    const btnEdit = document.createElement('button');
    btnEdit.type = 'button';
    btnEdit.className = 'ref-btn ref-btn--ghost btn-row-edit';
    btnEdit.textContent = 'Изменить';

    const btnSave = document.createElement('button');
    btnSave.type = 'button';
    btnSave.className = 'ref-btn ref-btn--primary btn-row-save is-hidden';
    btnSave.textContent = isNew ? 'Создать' : 'Сохранить';

    const btnCancel = document.createElement('button');
    btnCancel.type = 'button';
    btnCancel.className = 'ref-btn btn-row-cancel is-hidden';
    btnCancel.textContent = 'Отмена';

    const btnNoShow = document.createElement('button');
    btnNoShow.type = 'button';
    btnNoShow.className = 'ref-btn btn-row-no-show';
    btnNoShow.textContent = 'Не прибыл';
    btnNoShow.title = 'Заявка была, ТС не приехало';

    const btnHistory = document.createElement('button');
    btnHistory.type = 'button';
    btnHistory.className = 'ref-btn btn-row-history';
    btnHistory.textContent = 'Журнал';

    function setBtnVisible(btn, visible) {
      btn.classList.toggle('is-hidden', !visible);
    }

    function setEditing(on) {
      editing = on;
      UssApi.setRowFieldsEditable(tr, on);
      waybillsEditor?.setEditable?.(on);
      setBtnVisible(btnEdit, !on && !periodLocked);
      setBtnVisible(btnSave, on);
      setBtnVisible(btnCancel, on);
      const showExtra = !isNew && !!vehicle.id && !on;
      extraActions.classList.toggle('is-hidden', !showExtra);
      setBtnVisible(btnNoShow, showExtra && vehicle.arrival_status !== 'no_show' && !periodLocked);
      setBtnVisible(btnHistory, showExtra);
      tr.classList.toggle('vehicle-row-editing', on);
    }

    setEditing(isNew);

    btnEdit.addEventListener('click', () => setEditing(true));
    btnCancel.addEventListener('click', () => {
      if (isNew) tr.remove();
      else reload(nav);
    });

    btnSave.addEventListener('click', async () => {
      try {
        const payload = collectPayload(vehicle, fields, inputs, warehouseId, opDate);
        await UssApi.json('/api/uss/transport/vehicles', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        setStatus(isNew ? 'Строка создана.' : 'Сохранено.');
        reload(nav);
      } catch (e) {
        setStatus(e.message, true);
      }
    });

    btnNoShow.addEventListener('click', async () => {
      if (!window.confirm('Отметить ТС как «не прибыл»?')) return;
      try {
        await UssApi.json(`/api/uss/transport/vehicles/${vehicle.id}/no-show`, { method: 'POST', body: '{}' });
        setStatus('Отмечено: не прибыл.');
        reload(nav);
      } catch (e) {
        setStatus(e.message, true);
      }
    });

    btnHistory.addEventListener('click', async () => {
      try {
        const plate = vehicle.tractor_plate || '';
        await UssApi.showVehicleAuditDialog(vehicle.id, { plate });
      } catch (e) {
        setStatus(e.message, true);
      }
    });

    if (periodLocked) {
      btnEdit.disabled = true;
      btnNoShow.disabled = true;
    }

    mainActions.append(btnEdit, btnSave, btnCancel);
    extraActions.append(btnNoShow, btnHistory);
    tdBtn.append(mainActions, extraActions);
    tr.appendChild(tdBtn);
    return tr;
  }

  function renderVehicles(container, vehicles, contractId, warehouseId, opDate, schema, periodLocked, nav) {
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
      tbody.appendChild(vehicleRow(v, fields, warehouseId, opDate, false, periodLocked, nav));
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
        tbody.appendChild(vehicleRow(empty, fields, warehouseId, opDate, true, false, nav));
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
      writeNav({}, { warehouse_id: warehouseId, date: ctx.date });

      UssApi.renderToolbar(toolbarEl, {
        warehouses: ctx.warehouses,
        warehouseId,
        date: ctx.date,
        role,
        minDate: ctx.min_date,
        maxDate: ctx.max_date,
        onChange: (p) => {
          const prevWh = UssApi.qs().get('warehouse_id');
          const resetNav = prevWh && prevWh !== String(p.warehouse_id);
          writeNav(
            resetNav ? { clientId: '', contractId: '', panel: 'vehicles' } : {},
            { warehouse_id: p.warehouse_id, date: p.date },
          );
          load();
        },
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
      const nav = readNav();

      function clientVehicleCount(group) {
        const ids = new Set(group.contracts.map((c) => String(c.contract_id || c.id)));
        return (data.vehicles || []).filter((v) => ids.has(String(v.contract_id))).length;
      }

      function contractNav(clientId, contractId, panel) {
        return {
          clientId: clientId != null ? String(clientId) : nav.clientId,
          contractId: String(contractId),
          panel: panel || nav.panel || 'vehicles',
        };
      }

      function renderContractBlock(c, clientId) {
        const block = document.createElement('section');
        block.className = 'contract-block';
        const blockKey = UssApi.contractBlockKey(c);
        const cid = String(c.contract_id || c.id);
        const schema = data.schemas?.[blockKey] || data.schemas?.[cid] || {};
        const totals = UssApi.totalsMap(data.daily_totals?.[cid]);
        const vehicles = (data.vehicles || []).filter((v) => String(v.contract_id) === cid);
        const periodInputs = schema.period_inputs || [];
        const vehicleInputs = schema.vehicle_inputs || [];
        const periodLocked = UssApi.applyContractPeriodLock(block, data.period_locks?.[cid], monthLabel);
        const blockNav = contractNav(clientId, c.id, nav.contractId === cid ? nav.panel : 'vehicles');

        UssApi.renderContractHeader(block, c);
        UssApi.renderContractDateHint(block, c.date_hint);

        const tabsHost = document.createElement('div');
        block.appendChild(tabsHost);

        const tabs = [
          {
            label: 'Таблица транспорта',
            render: (panel) => {
              panel.replaceChildren();
              renderVehicles(panel, vehicles, c.id, data.warehouse_id, data.operation_date, schema, periodLocked, blockNav);
              if (vehicleInputs.length) {
                const hint = document.createElement('p');
                hint.className = 'muted uss-shift-field-hint';
                hint.textContent = 'Доп. услуги на строке ТС — колонки в таблице выше. Итоги за день без ТС — вкладка «Дополнительный».';
                panel.appendChild(hint);
              }
            },
          },
          {
            label: 'Дополнительный',
            render: (panel) => {
              panel.replaceChildren();
              UssApi.renderDailyReportForm(panel, {
                schema: {
                  period_inputs: periodInputs,
                },
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
                    reload({ ...blockNav, panel: 'daily' });
                  } catch (e) {
                    setStatus(e.message, true);
                  }
                },
              });
            },
          },
        ];

        let innerTabIndex = 0;
        if (nav.contractId === cid && nav.panel === 'daily') {
          innerTabIndex = 1;
        }

        UssApi.renderContractTabs(tabsHost, tabs, {
          initialIndex: innerTabIndex,
          onChange: (index) => {
            writeNav({
              clientId: clientId != null ? String(clientId) : nav.clientId,
              contractId: cid,
              panel: index === 0 ? 'vehicles' : 'daily',
            });
          },
        });
        return block;
      }

      if (clientGroups.length <= 1) {
        const onlyClientId = clientGroups[0]?.client_id;
        (clientGroups[0]?.contracts || data.contracts || []).forEach((c) => {
          contentEl.appendChild(renderContractBlock(c, onlyClientId));
        });
      } else {
        let clientTabIndex = 0;
        if (nav.clientId) {
          const idx = clientGroups.findIndex((g) => String(g.client_id) === nav.clientId);
          if (idx >= 0) clientTabIndex = idx;
        }
        const clientTabsHost = document.createElement('div');
        clientTabsHost.className = 'transport-client-tabs';
        contentEl.appendChild(clientTabsHost);
        UssApi.renderContractTabs(clientTabsHost, clientGroups.map((g) => ({
          label: `${g.client_name} (${clientVehicleCount(g)})`,
          render: (panel) => {
            const wrap = document.createElement('div');
            wrap.className = 'transport-client-panel';
            g.contracts.forEach((c) => wrap.appendChild(renderContractBlock(c, g.client_id)));
            panel.appendChild(wrap);
          },
        })), {
          initialIndex: clientTabIndex,
          onChange: (index) => {
            const g = clientGroups[index];
            writeNav({
              clientId: g.client_id != null ? String(g.client_id) : '',
              contractId: '',
              panel: 'vehicles',
            });
          },
        });
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
