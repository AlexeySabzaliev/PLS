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
        minDate: ctx.min_date,
        maxDate: ctx.max_date,
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
        contentEl.innerHTML = '<p class="muted">На выбранную дату нет договоров с действующим ДС. Выберите другую дату или проверьте доп. соглашения.</p>';
        setStatus(`Склад ${warehouseId}, ${data.report_date} — нет договоров на дату`);
        return;
      }

      const monthLabel = data.report_date?.slice(0, 7);

      (data.contracts || []).forEach((c) => {
        const block = document.createElement('section');
        block.className = 'contract-block';
        const blockKey = UssApi.contractBlockKey(c);
        const cid = String(c.contract_id || c.id);
        const schema = data.schemas?.[blockKey] || data.schemas?.[cid] || {};
        UssApi.renderContractHeader(block, c);
        UssApi.renderContractDateHint(block, c.date_hint);
        const periodLocked = UssApi.applyContractPeriodLock(block, data.period_locks?.[String(c.id)], monthLabel);
        const reportHost = document.createElement('div');
        block.appendChild(reportHost);
        UssApi.renderDailyReportForm(reportHost, {
          schema,
          readOnly: periodLocked,
          inventory: {
            areaEntries: areaAll,
            extraEntries: extraAll,
            onSave: async (area, extra) => {
              try {
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
              } catch (e) {
                setStatus(e.message, true);
              }
            },
          },
        });
        contentEl.appendChild(block);
      });

      setStatus(`Склад ${warehouseId}, ${data.report_date}`);
    } catch (e) {
      setStatus(e.message === 'unauthorized' ? 'Войдите в систему' : e.message, true);
    }
  }

  await load();
})();
