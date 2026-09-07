/** Админ: заглушки разделов и ролей (техработы) на весь портал. */
window.PlsMaintenanceAdmin = (function createMaintenanceAdmin() {
  let catalog = { modules: [], sections: [], roles: [] };
  let activeRows = [];
  let active = { sections: {}, roles: {} };
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
    if (!r.ok) throw new Error(data.message || data.error || 'HTTP ' + r.status);
    return data;
  }

  function setStatus(msg, isError) { ctx?.setStatus(msg, isError); }

  function moduleLabel(module) {
    const m = (catalog.modules || []).find((x) => x.module === module);
    return m ? m.label : module;
  }

  function blockRowHtml(type, key, label, state) {
    const targetKey = esc((type === 'role' ? 'role:' : 'section:') + key);
    const message = state ? state.message : '';
    const on = state && state.is_active;
    return `<tr data-maintenance-row data-type="${esc(type)}" data-key="${esc(key)}" data-target="${targetKey}">
      <td data-role-label>${esc(label)}</td>
      <td class="mnt-msg-cell"><input type="text" class="mnt-message" value="${esc(message)}" placeholder="Сообщение о работах"></td>
      <td><label class="mnt-toggle"><input type="checkbox" class="mnt-active"${on ? ' checked' : ''}> активна</label></td>
      <td class="mnt-actions">
        <button type="button" class="btn-secondary mnt-save">Сохранить</button>
        ${state ? '<button type="button" class="btn-danger mnt-remove">Убрать</button>' : ''}
      </td>
    </tr>`;
  }

  function renderPanel() {
    if (!ctx) return;
    const pb = ctx.panelEl;
    let html = '<p class="muted">Заглушка блокирует только выбранный раздел/роль (для всех, кроме админа). Остальной портал продолжает работать.</p>';
    html += '<h2 class="mnt-block">Разделы</h2>';
    html += '<table class="ref-table mnt-table"><tbody>';
    (catalog.sections || []).forEach((s) => {
      html += blockRowHtml('section', s.key, s.label, active.sections[s.key] || null);
    });
    html += '</tbody></table>';
    html += '<h2 class="mnt-block">Роли</h2>';
    html += '<table class="ref-table mnt-table"><tbody>';
    (catalog.roles || []).forEach((r) => {
      html += blockRowHtml('role', r.code, r.name, active.roles[r.code] || null);
    });
    html += '</tbody></table>';
    pb.innerHTML = html;
    attachHandlers(pb);
  }

  function attachHandlers(pb) {
    pb.querySelectorAll('[data-maintenance-row]').forEach((row) => {
      const type = row.dataset.type;
      const key = row.dataset.key;
      row.querySelector('.mnt-save').addEventListener('click', async () => {
        const message = row.querySelector('.mnt-message').value.trim();
        const isActive = row.querySelector('.mnt-active').checked;
        if (!message) { setStatus('Укажите сообщение для заглушки', true); return; }
        try {
          await api('/api/maintenance', {
            method: 'POST',
            body: JSON.stringify({
              target_type: type,
              target_key: key,
              message,
              is_active: isActive,
            }),
          });
          setStatus((type === 'role' ? 'Роль' : 'Раздел') + ' — заглушка сохранена');
          await refresh();
        } catch (e) { setStatus(e.message, true); }
      });
      const rmBtn = row.querySelector('.mnt-remove');
      if (rmBtn) {
        rmBtn.addEventListener('click', async () => {
          const activeRow = activeRows.find((r) => r.target_type === type && r.target_key === key);
          if (!activeRow) return;
          try {
            await api('/api/maintenance/' + activeRow.id, { method: 'DELETE' });
            setStatus('Заглушка снята');
            await refresh();
          } catch (e) { setStatus(e.message, true); }
        });
      }
    });
  }

  async function refresh() {
    const [act, cat] = await Promise.all([api('/api/maintenance'), api('/api/maintenance/catalog')]);
    catalog = cat;
    activeRows = act || [];
    active = { sections: {}, roles: {} };
    activeRows.forEach((r) => {
      const map = r.target_type === 'role' ? active.roles : active.sections;
      map[r.target_key] = r;
    });
    renderPanel();
  }

  function render() {
    refresh().catch((e) => {
      if (ctx?.panelEl) ctx.panelEl.innerHTML = '';
      setStatus(e.message, true);
    });
  }

  return {
    render(opts) {
      ctx = opts;
      render();
    },
  };
}());