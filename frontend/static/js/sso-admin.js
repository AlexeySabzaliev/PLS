/** Админ: лист ожидания SSO */
(function initSsoAdmin() {
  const statusEl = document.getElementById('status');
  const listEl = document.getElementById('requests');

  function setStatus(msg, isError) {
    statusEl.textContent = msg;
    statusEl.className = isError ? 'status error' : 'status';
  }

  async function api(url, options = {}) {
    const r = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      credentials: 'same-origin',
      ...options,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
    return data;
  }

  function esc(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;');
  }

  function render(items) {
    if (!items.length) {
      listEl.innerHTML = '<p class="muted">Нет ожидающих заявок.</p>';
      return;
    }
    listEl.innerHTML = `<table class="data-table"><thead><tr>
      <th>Email</th><th>Имя</th><th>Попыток</th><th>Последний вход</th><th></th>
    </tr></thead><tbody>${items.map((row) => `
      <tr data-id="${row.id}">
        <td>${esc(row.email)}</td>
        <td>${esc(row.display_name || '—')}</td>
        <td>${row.login_attempts}</td>
        <td>${esc(row.last_seen_at || '')}</td>
        <td class="row-actions">
          <button type="button" class="btn-approve">Одобрить</button>
          <button type="button" class="btn-dismiss btn-del">Отклонить</button>
        </td>
      </tr>`).join('')}</tbody></table>`;

    listEl.querySelectorAll('.btn-approve').forEach((btn) => {
      btn.addEventListener('click', () => act(btn.closest('tr').dataset.id, 'approve'));
    });
    listEl.querySelectorAll('.btn-dismiss').forEach((btn) => {
      btn.addEventListener('click', () => act(btn.closest('tr').dataset.id, 'dismiss'));
    });
  }

  async function act(id, kind) {
    try {
      await api(`/api/admin/sso-requests/${id}/${kind}`, { method: 'POST', body: '{}' });
      setStatus(kind === 'approve' ? 'Пользователь создан/активирован.' : 'Заявка отклонена.');
      await load();
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function load() {
    const data = await api('/api/admin/sso-requests');
    render(data.items || []);
    setStatus(`Ожидают: ${data.pending_count ?? 0}`);
  }

  load().catch((e) => setStatus(e.message, true));
})();
