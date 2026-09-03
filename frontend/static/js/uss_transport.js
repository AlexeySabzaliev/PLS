/** Транспортная смена — UI из report_schema */

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



  function setStatus(msg, isError) {

    statusEl.textContent = msg;

    statusEl.className = isError ? 'status error' : 'status';

  }



  function vehicleLabel(v) {

    const parts = [v.tractor_plate, v.trailer_plate].filter(Boolean);

    return parts.length ? parts.join(' / ') : 'новое ТС';

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

      : 'Нажмите «С охраны» для загрузки ТС из портала';

    toolbarHost.querySelector('.toolbar')?.appendChild(hint);

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

        onChange: (p) => {

          UssApi.setQs(p);

          load();

        },

      });



      const syncBtn = document.createElement('button');

      syncBtn.type = 'button';

      syncBtn.id = 'btn-sync-security';

      syncBtn.textContent = 'С охраны';

      syncBtn.className = 'toolbar-btn btn-primary-sm';

      syncBtn.title = 'Загрузить ТС из портала охраны (security.bsh-ru.ru)';

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

        UssApi.renderContractHeader(block, c);
        UssApi.renderContractDateHint(block, c.date_hint);
        UssApi.applyContractPeriodLock(block, data.period_locks?.[cid], monthLabel);

        const tabsHost = document.createElement('div');
        block.appendChild(tabsHost);

        const tabs = [
          {
            label: 'ТС',
            render: (panel) => {
              renderVehicles(
                panel, vehicles, c.id, data.warehouse_id, data.operation_date, schema,
              );
            },
          },
        ];

        if (periodInputs.length) {
          tabs.push({
            label: 'Дополнительный',
            render: (panel) => {
              UssApi.renderDailyReportForm(panel, {
                schema: { period_inputs: periodInputs },
                totals,
                onPeriodSave: async (entries) => {
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

      setStatus(e.message === 'unauthorized' ? 'Войдите через SSO или /api/auth/login' : e.message, true);

    }

  }



  function renderVehicles(container, vehicles, contractId, warehouseId, opDate, schema) {
    const fields = schema.vehicle_fixed_fields || [];

    container.innerHTML = '';
    container.className = 'vehicles-section';

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

    const thAct = document.createElement('th');

    thAct.textContent = '';

    thAct.className = 'col-actions';

    hr.appendChild(thAct);

    thead.appendChild(hr);

    table.appendChild(thead);



    const tbody = document.createElement('tbody');



    vehicles.forEach((v) => {

      const tr = vehicleRow(v, fields, warehouseId, opDate, false);

      if (v.source === 'security') {

        tr.classList.add('vehicle-from-security');

        const plateTd = tr.querySelector('.col-plate');

        if (plateTd && !plateTd.querySelector('.security-badge')) {

          const badge = document.createElement('span');

          badge.className = 'security-badge';

          badge.textContent = 'охрана';

          badge.title = 'Строка загружена из портала охраны';

          plateTd.appendChild(badge);

        }

      }

      tbody.appendChild(tr);

    });

    table.appendChild(tbody);

    wrap.appendChild(table);

    container.appendChild(wrap);



    const addBtn = document.createElement('button');

    addBtn.type = 'button';

    addBtn.textContent = '+ Добавить ТС';

    addBtn.addEventListener('click', () => {

      const empty = { contract_id: contractId, report_quantities: {}, waybills: [] };

      tbody.appendChild(vehicleRow(empty, fields, warehouseId, opDate, true));

    });

    container.appendChild(addBtn);

  }



  function fieldValue(vehicle, fieldDef) {
    if (fieldDef.tariff_input || (fieldDef.field && fieldDef.field.startsWith('rq_'))) {
      const code = fieldDef.billing_line_code || fieldDef.field.slice(3);
      return vehicle.report_quantities?.[code];
    }
    return vehicle[fieldDef.field];
  }

  function vehicleRow(vehicle, fields, warehouseId, opDate, isNew) {

    const tr = document.createElement('tr');

    const inputs = {};

    let waybillsEditor = null;



    fields.forEach((f) => {

      const td = document.createElement('td');

      td.className = COL_CLASS[f.field] || '';

      if (f.input_type === 'waybill_column' || f.input_type === 'mx_column') {

        if (!waybillsEditor) {

          waybillsEditor = UssApi.createWaybillsEditor(

            vehicle.waybills,

            vehicle.operation_type_code || 'inbound',

            true,

          );

          inputs.waybills = waybillsEditor;

        }

        td.appendChild(

          f.input_type === 'waybill_column' ? waybillsEditor.waybillCol : waybillsEditor.mxCol,

        );

      } else {

        const inp = UssApi.renderSchemaField(f, fieldValue(vehicle, f), { vehicleTypes });

        inputs[f.field] = inp;

        td.appendChild(inp);

        if (f.field === 'operation_type_code') {

          inp.addEventListener('change', () => {

            waybillsEditor?.updateOpType(inp.value);

          });

        }

      }

      tr.appendChild(td);

    });



    const tdBtn = document.createElement('td');

    tdBtn.className = 'col-actions';

    const save = document.createElement('button');

    save.type = 'button';

    save.textContent = isNew ? 'Создать' : 'Сохранить';

    save.addEventListener('click', async () => {

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
      if (Object.keys(reportQuantities).length) {
        payload.report_quantities = reportQuantities;
      }

      await UssApi.json('/api/uss/transport/vehicles', {

        method: 'POST',

        body: JSON.stringify(payload),

      });

      load();

    });

    tdBtn.appendChild(save);

    tr.appendChild(tdBtn);

    return tr;

  }



  await load();

})();


