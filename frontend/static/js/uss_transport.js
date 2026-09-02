/** Транспортная смена — UI из report_schema */
(async function initTransportShift() {
  const statusEl = document.getElementById('status');
  const toolbarEl = document.getElementById('toolbar');
  const contentEl = document.getElementById('content');
  const role = 'transport_logistics';
  let vehicleTypes = [];

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
      setStatus(`Охрана: +${data.synced} ТС (${data.source})`);
      load();
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function load() {
    const q = UssApi.qs();
    const date = q.get('date') || UssApi.today();
    let warehouseId = q.get('warehouse_id');

    setStatus('Загрузка…');
    try {
      const ctx = await UssApi.json(
        `/api/uss/context?role=${role}&date=${date}${warehouseId ? `&warehouse_id=${warehouseId}` : ''}`
      );
      warehouseId = String(ctx.warehouse_id);
      UssApi.setQs({ warehouse_id: warehouseId, date: ctx.date });

      UssApi.renderToolbar(toolbarEl, {
        warehouses: ctx.warehouses,
        warehouseId,
        date: ctx.date,
        role,
        onChange: (p) => {
          UssApi.setQs(p);
          load();
        },
      });

      const syncBtn = document.createElement('button');
      syncBtn.type = 'button';
      syncBtn.id = 'btn-sync-security';
      syncBtn.textContent = 'С охраны';
      syncBtn.className = 'toolbar-btn';
      syncBtn.addEventListener('click', () => syncSecurity(warehouseId, ctx.date));
      toolbarEl.querySelector('.toolbar')?.appendChild(syncBtn);

      const data = await UssApi.json(
        `/api/uss/transport/shift?warehouse_id=${warehouseId}&date=${ctx.date}`
      );
      vehicleTypes = data.vehicle_types || [];

      contentEl.innerHTML = '';
      if (!data.contracts?.length) {
        setStatus('Нет активных договоров на этом складе.');
        return;
      }

      data.contracts.forEach((c) => {
        const block = document.createElement('section');
        block.className = 'contract-block';
        const cid = String(c.id);
        const schema = data.schemas?.[cid] || {};
        const totals = UssApi.totalsMap(data.daily_totals?.[cid]);
        const vehicles = (data.vehicles || []).filter((v) => String(v.contract_id) === cid);

        block.innerHTML = `<h2>Договор ${c.number}</h2>`;
        const vehSec = document.createElement('div');
        vehSec.className = 'vehicles-section';
        renderVehicles(vehSec, vehicles, c.id, data.warehouse_id, data.operation_date, schema);
        block.appendChild(vehSec);

        const periodInputs = schema.period_inputs || [];
        if (periodInputs.length) {
          const dailyEl = document.createElement('div');
          dailyEl.className = 'daily-section';
          block.appendChild(dailyEl);
          UssApi.renderPeriodForm(dailyEl, schema, totals, async (entries) => {
            await UssApi.json('/api/uss/transport/daily', {
              method: 'POST',
              body: JSON.stringify({
                warehouse_id: data.warehouse_id,
                contract_id: c.id,
                report_date: data.operation_date,
                entries,
              }),
            });
            setStatus('Суточные сохранены.');
            load();
          });
        }

        contentEl.appendChild(block);
      });

      const sec = data.security?.source === 'demo' ? ' (демо-охрана)' : '';
      setStatus(`Склад ${warehouseId}, ${data.operation_date}${sec}`);
    } catch (e) {
      setStatus(e.message === 'unauthorized' ? 'Войдите через SSO или /api/auth/login' : e.message, true);
    }
  }

  function renderVehicles(container, vehicles, contractId, warehouseId, opDate, schema) {
    const fields = schema.vehicle_fixed_fields || [];
    const vInputs = schema.vehicle_inputs || [];
    const head = document.createElement('h3');
    head.textContent = `ТС (${vehicles.length})`;
    container.appendChild(head);

    const wrap = document.createElement('div');
    wrap.className = 'table-scroll';
    const table = document.createElement('table');
    table.className = 'data-table transport-table';
    const thead = document.createElement('thead');
    const hr = document.createElement('tr');
    fields.forEach((f) => {
      const th = document.createElement('th');
      th.textContent = f.label;
      hr.appendChild(th);
    });
    vInputs.forEach((inp) => {
      const th = document.createElement('th');
      th.textContent = inp.name;
      th.title = inp.billing_line_code;
      hr.appendChild(th);
    });
    const thAct = document.createElement('th');
    thAct.textContent = '';
    hr.appendChild(thAct);
    thead.appendChild(hr);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    vehicles.forEach((v) => tbody.appendChild(vehicleRow(v, fields, vInputs, warehouseId, opDate)));
    table.appendChild(tbody);
    wrap.appendChild(table);
    container.appendChild(wrap);

    const addBtn = document.createElement('button');
    addBtn.type = 'button';
    addBtn.textContent = '+ Добавить ТС';
    addBtn.addEventListener('click', () => {
      const empty = { contract_id: contractId, report_quantities: {}, waybills: [] };
      const tr = vehicleRow(empty, fields, vInputs, warehouseId, opDate, true);
      tbody.appendChild(tr);
    });
    container.appendChild(addBtn);
  }

  function vehicleRow(vehicle, fields, vInputs, warehouseId, opDate, isNew) {
    const tr = document.createElement('tr');
    const inputs = {};
    const rqInputs = {};
    const rq = vehicle.report_quantities || {};
    let waybillsBlock = null;

    fields.forEach((f) => {
      const td = document.createElement('td');
      if (f.input_type === 'waybills') {
        waybillsBlock = UssApi.renderWaybillsBlock(
          vehicle.waybills,
          vehicle.operation_type_code || 'inbound',
          true,
        );
        inputs.waybills = waybillsBlock;
        td.appendChild(waybillsBlock);
      } else {
        const inp = UssApi.renderSchemaField(f, vehicle[f.field], { vehicleTypes });
        inputs[f.field] = inp;
        td.appendChild(inp);
        if (f.field === 'operation_type_code') {
          inp.addEventListener('change', () => {
            waybillsBlock?.updateMxLabels(inp.value);
          });
        }
      }
      tr.appendChild(td);
    });
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
    const save = document.createElement('button');
    save.type = 'button';
    save.textContent = isNew ? 'Создать' : 'Сохранить';
    save.addEventListener('click', async () => {
      const payload = {
        warehouse_id: warehouseId,
        contract_id: vehicle.contract_id,
        operation_date: opDate,
        report_quantities: {},
      };
      if (vehicle.id) payload.id = vehicle.id;
      fields.forEach((f) => {
        if (f.input_type === 'waybills') {
          payload.waybills = inputs.waybills?.collect?.() || [];
          return;
        }
        const v = inputs[f.field].value;
        payload[f.field] = v === '' ? null : v;
      });
      Object.keys(rqInputs).forEach((code) => {
        const v = rqInputs[code].value;
        if (v !== '') payload.report_quantities[code] = Number(v);
      });
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
