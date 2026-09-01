(async () => {
  const params = new URLSearchParams(location.search);
  const wh = params.get('warehouse_id') || '1';
  const date = params.get('date') || new Date().toISOString().slice(0, 10);
  const status = document.getElementById('status');
  const box = document.getElementById('vehicles');
  try {
    const r = await fetch(`/api/uss/transport/shift?warehouse_id=${wh}&date=${date}`);
    if (!r.ok) throw new Error(r.status);
    const data = await r.json();
    status.textContent = `Склад ${data.warehouse_id}, ${data.operation_date}: ${data.vehicles.length} ТС`;
    box.innerHTML = data.vehicles.map(v => `<div>${v.plate_number || '—'} — ${v.volume_document_m3} м³</div>`).join('');
  } catch (e) {
    status.textContent = 'Требуется вход (SSO или /api/auth/login)';
  }
})();
