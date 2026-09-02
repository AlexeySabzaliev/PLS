/** Транспортная смена — UI из report_schema */
(async function initTransportShift() {
  const statusEl = document.getElementById('status');
  const toolbarEl = document.getElementById('toolbar');
  const contentEl = document.getElementById('content');
  const role = 'transport_logistics';

  function setStatus(msg, isError) {
    statusEl.textContent = msg;
    statusEl.className = isError ? 'status error' : 'status';
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

      const data = await UssApi.json(
        `/api/uss/transport/shift?warehouse_id=${warehouseId}&date=${ctx.date}`
      );

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

        contentEl.appendChild(block);
      });

      setStatus(`Склад ${warehouseId}, ${data.operation_date}`);
    } catch (e) {
      setStatus(e.message === 'unauthorized' ? 'Войдите через SSO или /api/auth/login' : e.message, true);
    }
  }

  function renderVehicles(container, vehicles, contractId, warehouseId, opDate, schema) {
    const fields = schema.vehicle_fixed_fields || [];
    const head = document.createElement('h3');
    head.textContent = `ТС (${vehicles.length})`;
    container.appendChild(head);

    const table = document.createElement('table');
    table.className = 'data-table';
    const thead = document.createElement('thead');
    const hr = document.createElement('tr');
    fields.forEach((f) => {
      const th = document.createElement('th');
      th.textContent = f.label;
      hr.appendChild(th);
    });
    const thAct = document.createElement('th');
    thAct.textContent = '';
    hr.appendChild(thAct);
    thead.appendChild(hr);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    vehicles.forEach((v) => tbody.appendChild(vehicleRow(v, fields, warehouseId, opDate)));
    table.appendChild(tbody);
    container.appendChild(table);

    const addBtn = document.createElement('button');
    addBtn.type = 'button';
    addBtn.textContent = '+ Добавить ТС';
    addBtn.addEventListener('click', () => {
      const empty = { contract_id: contractId };
      const tr = vehicleRow(empty, fields, warehouseId, opDate, true);
      tbody.appendChild(tr);
    });
    container.appendChild(addBtn);
  }

  function vehicleRow(vehicle, fields, warehouseId, opDate, isNew) {
    const tr = document.createElement('tr');
    const inputs = {};
    fields.forEach((f) => {
      const td = document.createElement('td');
      const inp = document.createElement('input');
      inp.name = f.field;
      if (f.input_type === 'number') inp.type = 'number';
      else if (f.input_type === 'datetime-local') inp.type = 'datetime-local';
      else inp.type = 'text';
      let val = vehicle[f.field];
      if (f.input_type === 'datetime-local' && val) {
        val = val.slice(0, 16);
      }
      inp.value = val ?? '';
      inputs[f.field] = inp;
      td.appendChild(inp);
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
      };
      if (vehicle.id) payload.id = vehicle.id;
      fields.forEach((f) => { payload[f.field] = inputs[f.field].value || null; });
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
