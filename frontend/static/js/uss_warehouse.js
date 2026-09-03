/** Складская смена — только operation_daily_totals, без ТС */
(async function initWarehouseShift() {
  const statusEl = document.getElementById('status');
  const toolbarEl = document.getElementById('toolbar');
  const contentEl = document.getElementById('content');
  const role = 'warehouse_logistics';

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
        `/api/uss/warehouse/shift?warehouse_id=${warehouseId}&date=${ctx.date}`
      );

      contentEl.innerHTML = '';
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
        const totals = UssApi.totalsMap(data.daily_totals?.[cid]);

        UssApi.renderContractHeader(block, c);
        UssApi.renderContractDateHint(block, c.date_hint);
        UssApi.applyContractPeriodLock(block, data.period_locks?.[cid], monthLabel);
        const reportHost = document.createElement('div');
        block.appendChild(reportHost);
        UssApi.renderDailyReportForm(reportHost, {
          schema,
          totals,
          onPeriodSave: async (entries) => {
            await UssApi.json('/api/uss/warehouse/shift', {
              method: 'POST',
              body: JSON.stringify({
                warehouse_id: data.warehouse_id,
                contract_id: c.id,
                report_date: data.report_date,
                entries,
              }),
            });
            setStatus('Сохранено.');
            load();
          },
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
