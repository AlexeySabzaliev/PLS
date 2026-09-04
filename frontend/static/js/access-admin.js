/** Админ: пользователи, роли и заявки на восстановление пароля. */
window.PlsAccessAdmin = (function createAccessAdmin() {
  let meta = { roles: [], warehouses: [] };
  let users = [];
  let ctx = null;

  function esc(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
  }

  async function api(url, options = {}) {
    const r = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      credentials: 'same-origin',
      ...options,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.message || data.error || `HTTP ${r.status}`);
    return data;
  }

  function panel() {
    return ctx?.panelEl;
  }

  function setStatus(msg, isError) {
    ctx?.setStatus(msg, isError);
  }

  function rolesHtml(container, prefix, selectedCodes = []) {
    if (!container) return;
    const selected = new Set(selectedCodes);
    if (!meta.roles?.length) {
      container.innerHTML = '<p class="muted">Роли не заданы.</p>';
      return;
    }
    let html = '<fieldset class="access-role-group"><legend>Роли</legend><div class="access-role-checks">';
    meta.roles.forEach((r) => {
      const id = `${prefix}-role-${r.code}`;
      html += `<label class="access-checkbox" for="${id}"><input type="checkbox" id="${id}" data-role="${esc(r.code)}"${selected.has(r.code) ? ' checked' : ''}> ${esc(r.name)}</label>`;
    });
    html += '</div></fieldset>';
    container.innerHTML = html;
  }

  function warehousesHtml(container, prefix, selectedIds = []) {
    if (!container) return;
    const selected = new Set((selectedIds || []).map(String));
    if (!meta.warehouses.length) {
      container.innerHTML = '<p class="muted">Склады не заданы в справочнике.</p>';
      return;
    }
    let html = '<fieldset class="access-role-group"><legend>Доступ к складам</legend><div class="access-role-checks">';
    meta.warehouses.forEach((w) => {
      const id = `${prefix}-wh-${w.id}`;
      html += `<label class="access-checkbox" for="${id}"><input type="checkbox" id="${id}" data-warehouse="${w.id}"${selected.has(String(w.id)) ? ' checked' : ''}> ${esc(w.code)} — ${esc(w.name)}${w.is_active === false ? ' (неакт.)' : ''}</label>`;
    });
    html += '</div></fieldset>';
    container.innerHTML = html;
  }

  function readRolesFrom(container) {
    return [...container.querySelectorAll('input[data-role]:checked')].map((el) => el.dataset.role);
  }

  function readWarehousesFrom(container) {
    return [...container.querySelectorAll('input[data-warehouse]:checked')].map((el) => Number(el.dataset.warehouse));
  }

  function formatRoles(codes) {
    if (!codes?.length) return '<span class="muted">—</span>';
    const map = Object.fromEntries((meta.roles || []).map((r) => [r.code, r.name]));
    return codes.map((c) => esc(map[c] || c)).join(', ');
  }

  function shellHtml() {
    return `
      <h2>Пользователи и доступ</h2>
      <p class="muted">Новые пользователи регистрируются на главной (роль «Просмотр отчётов»). Здесь — сброс паролей и назначение ролей.</p>
      <section class="access-panel">
        <h3>Восстановление пароля <span id="access-pending-badge" class="access-badge">0</span></h3>
        <p class="muted">Пользователь забыл пароль и отправил заявку с главной страницы.</p>
        <div id="access-requests"></div>
      </section>
      <section class="access-panel">
        <h3>Пользователи</h3>
        <label class="access-checkbox access-filter"><input type="checkbox" id="access-show-inactive" checked> Показывать неактивных</label>
        <div id="access-users-wrap"></div>
      </section>
      <dialog id="access-dlg-edit" class="access-dialog">
        <form method="dialog" id="access-form-edit" class="access-user-form">
          <h3>Редактирование</h3>
          <p class="muted" id="access-edit-email"></p>
          <input type="hidden" name="user_id">
          <label class="access-field"><span>ФИО</span><input type="text" name="full_name"></label>
          <div id="access-edit-roles" class="access-role-groups"></div>
          <div id="access-edit-wh" class="access-wh-list"></div>
          <label class="access-field"><span>Новый пароль</span><input type="password" name="new_password" autocomplete="new-password" placeholder="Сброс пароля"></label>
          <label class="access-checkbox"><input type="checkbox" name="is_active" checked> Активен</label>
          <div class="access-form-actions">
            <button type="submit" class="ref-btn ref-btn--primary">Сохранить</button>
            <button type="button" class="ref-btn" id="access-edit-cancel">Отмена</button>
          </div>
        </form>
      </dialog>`;
  }

  function renderPending(items) {
    const badge = panel()?.querySelector('#access-pending-badge');
    const host = panel()?.querySelector('#access-requests');
    if (badge) badge.textContent = String(items.length);
    if (!host) return;
    if (!items.length) {
      host.innerHTML = '<p class="muted">Нет ожидающих заявок.</p>';
      return;
    }
    host.innerHTML = items.map((row) => `
      <article class="access-request-card" data-id="${row.id}">
        <div class="access-request-head">
          <strong>${esc(row.email)}</strong>
          <span class="muted">${esc(row.display_name || '')}</span>
          <span class="muted">запросов: ${row.request_count}</span>
        </div>
        ${row.user_note ? `<p class="muted">Комментарий: ${esc(row.user_note)}</p>` : ''}
        <form class="access-reset-form">
          <label class="access-field"><span>Новый пароль</span>
            <input type="password" class="reset-password" required autocomplete="new-password" placeholder="Пароль для пользователя"></label>
          <div class="access-form-actions">
            <button type="submit" class="ref-btn ref-btn--primary btn-approve">Установить пароль</button>
            <button type="button" class="ref-btn btn-dismiss">Отклонить</button>
          </div>
        </form>
      </article>`).join('');

    host.querySelectorAll('.access-reset-form').forEach((form) => {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        approveReset(form.closest('.access-request-card'));
      });
    });
    host.querySelectorAll('.btn-dismiss').forEach((btn) => {
      btn.addEventListener('click', () => dismissReset(btn.closest('.access-request-card')?.dataset.id));
    });
  }

  async function approveReset(card) {
    if (!card?.dataset?.id) {
      setStatus('Не найдена карточка заявки', true);
      return;
    }
    const password = card.querySelector('.reset-password')?.value || '';
    if (!password) {
      setStatus('Укажите новый пароль', true);
      return;
    }
    const submitBtn = card.querySelector('.btn-approve');
    try {
      if (submitBtn) submitBtn.disabled = true;
      await api(`/api/admin/password-reset-requests/${card.dataset.id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ password }),
      });
      setStatus('Пароль установлен, заявка закрыта.');
      await loadAll();
    } catch (err) {
      setStatus(err.message || 'Не удалось установить пароль', true);
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  async function dismissReset(id) {
    if (!id) {
      setStatus('Не найдена заявка', true);
      return;
    }
    if (!window.confirm('Отклонить заявку?')) return;
    try {
      await api(`/api/admin/password-reset-requests/${id}/dismiss`, { method: 'POST', body: '{}' });
      setStatus('Заявка отклонена.');
      await loadPending();
    } catch (err) {
      setStatus(err.message || 'Не удалось отклонить заявку', true);
    }
  }

  function renderUsers() {
    const host = panel()?.querySelector('#access-users-wrap');
    const showAll = panel()?.querySelector('#access-show-inactive')?.checked;
    const list = showAll ? users : users.filter((u) => u.is_active);
    if (!host) return;
    if (!list.length) {
      host.innerHTML = '<p class="muted">Нет пользователей.</p>';
      return;
    }
    host.innerHTML = `<table class="data-table access-users-table"><thead><tr>
      <th>Email</th><th>Имя</th><th>Роли</th><th>Склады</th><th>Статус</th><th></th>
    </tr></thead><tbody>${list.map((u) => `
      <tr data-user-id="${u.id}">
        <td>${esc(u.email)}</td>
        <td>${esc(u.full_name || '—')}</td>
        <td>${formatRoles(u.role_codes)}</td>
        <td>${(u.warehouse_ids || []).length || '<span class="muted">—</span>'}</td>
        <td>${u.is_active ? '<span class="cr-status cr-status--ok">активен</span>' : '<span class="cr-status cr-status--muted">выкл</span>'}${u.has_password ? '' : ' <span class="muted">(без пароля)</span>'}</td>
        <td><button type="button" class="ref-btn btn-edit-user">Изменить</button></td>
      </tr>`).join('')}</tbody></table>`;
    host.querySelectorAll('.btn-edit-user').forEach((btn) => {
      btn.addEventListener('click', () => openEdit(Number(btn.closest('tr').dataset.userId)));
    });
  }

  function openEdit(userId) {
    const user = users.find((u) => u.id === userId);
    const form = panel()?.querySelector('#access-form-edit');
    const dlg = panel()?.querySelector('#access-dlg-edit');
    if (!user || !form || !dlg) return;
    form.elements.user_id.value = userId;
    panel().querySelector('#access-edit-email').textContent = user.email;
    form.elements.full_name.value = user.full_name || '';
    form.elements.is_active.checked = user.is_active !== false;
    if (form.elements.new_password) form.elements.new_password.value = '';
    rolesHtml(panel().querySelector('#access-edit-roles'), 'edit', user.role_codes || []);
    warehousesHtml(panel().querySelector('#access-edit-wh'), 'editwh', user.warehouse_ids || []);
    dlg.showModal();
  }

  async function loadPending() {
    const data = await api('/api/admin/password-reset-requests');
    meta.roles = data.roles || meta.roles;
    meta.warehouses = data.warehouses || meta.warehouses;
    renderPending(data.items || []);
    return data.pending_count ?? 0;
  }

  async function loadUsers() {
    const showInactive = panel()?.querySelector('#access-show-inactive')?.checked;
    const q = showInactive ? '' : '?include_inactive=0';
    const data = await api(`/api/admin/users${q}`);
    meta.roles = data.roles || meta.roles;
    meta.warehouses = data.warehouses || meta.warehouses;
    users = data.items || [];
    renderUsers();
  }

  async function loadAll() {
    const pending = await loadPending();
    await loadUsers();
    setStatus(`Пользователей: ${users.length}. Заявок на пароль: ${pending}.`);
  }

  function bindEvents() {
    const p = panel();
    p.querySelector('#access-form-edit')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      const userId = Number(form.elements.user_id.value);
      await api(`/api/admin/users/${userId}`, {
        method: 'PUT',
        body: JSON.stringify({
          full_name: form.elements.full_name.value,
          is_active: form.elements.is_active.checked,
          role_codes: readRolesFrom(form),
          warehouse_ids: readWarehousesFrom(form),
        }),
      });
      const newPassword = form.elements.new_password?.value || '';
      if (newPassword) {
        await api(`/api/admin/users/${userId}/password`, {
          method: 'POST',
          body: JSON.stringify({ password: newPassword }),
        });
      }
      p.querySelector('#access-dlg-edit')?.close();
      setStatus('Сохранено.');
      await loadAll();
    });
    p.querySelector('#access-edit-cancel')?.addEventListener('click', () => {
      p.querySelector('#access-dlg-edit')?.close();
    });
    p.querySelector('#access-show-inactive')?.addEventListener('change', () => {
      loadUsers().catch((err) => setStatus(err.message, true));
    });
  }

  async function render(options) {
    ctx = options;
    ctx.setHintVisible?.(false);
    ctx.panelEl.innerHTML = shellHtml();
    bindEvents();
    setStatus('Загрузка…');
    try {
      await loadAll();
    } catch (err) {
      setStatus(err.message, true);
    }
  }

  return { render };
})();
