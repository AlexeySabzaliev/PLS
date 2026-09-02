/** Управление запасами — shift_reports по схеме договора */
(async function initInventoryShift() {
  const statusEl = document.getElementById('status');
  const toolbarEl = document.getElementById('toolbar');
  const contentEl = document.getElementById('content');
  const role = 'inventory_management';

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
        `/api/uss/inventory/shift?warehouse_id=${warehouseId}&date=${ctx.date}`
      );

      contentEl.innerHTML = '';
      const areaAll = data.area_entries || {};
      const extraAll = data.extra_entries || {};

      if (!data.contracts?.length) {
        setStatus('Нет договоров для ввода.');
        return;
      }

      data.contracts.forEach((c) => {
        const block = document.createElement('section');
        block.className = 'contract-block';
        const schema = data.schemas?.[String(c.id)] || {};
        block.innerHTML = `<h2>Договор ${c.number}</h2>`;
        const formEl = document.createElement('div');
        block.appendChild(formEl);
        UssApi.renderInventoryForm(formEl, schema, areaAll, extraAll, async (area, extra) => {
          await UssApi.json('/api/uss/inventory/shift', {
            method: 'POST',
            body: JSON.stringify({
              warehouse_id: data.warehouse_id,
              report_date: data.report_date,
              area_entries: area,
              extra_entries: extra,
            }),
          });
          setStatus('Сохранено.');
          load();
        });
        contentEl.appendChild(block);
      });

      setStatus(`Склад ${warehouseId}, ${data.report_date}`);
    } catch (e) {
      setStatus(e.message === 'unauthorized' ? 'Войдите через SSO или /api/auth/login' : e.message, true);
    }
  }

  await load();
})();
