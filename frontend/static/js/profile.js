/** Профиль пользователя: ФИО и смена пароля */
(function profilePage() {
  const ROLE_LABELS = {
    admin: 'Администратор',
    commercial_logistics: 'Коммерческая логистика',
    transport_logistics: 'Транспортная логистика',
    warehouse_logistics: 'Складская логистика',
    inventory_management: 'Управление запасами',
    ved_specialist: 'Специалист ВЭД',
    reports_viewer: 'Просмотр отчётов',
  };

  function setStatus(msg, isError) {
    const el = document.getElementById('profile-status');
    if (!el) return;
    el.textContent = msg || '';
    el.className = isError ? 'status error' : 'status ok';
  }

  async function api(url, options = {}) {
    const r = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      credentials: 'same-origin',
      ...options,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      const err = new Error(data.message || data.error || `HTTP ${r.status}`);
      err.code = data.error;
      throw err;
    }
    return data;
  }

  function policyHint(policy) {
    if (!policy) return '';
    return `Не менее ${policy.min_length} символов, буква и цифра`;
  }

  function renderProfile(user) {
    document.getElementById('profile-email').value = user.email || '';
    document.getElementById('profile-full-name').value = user.full_name || '';
    const roles = (user.role_codes || []).map((c) => ROLE_LABELS[c] || c).join(', ');
    document.getElementById('profile-roles').textContent = roles ? `Роли: ${roles}` : 'Роли не назначены';

    const policy = user.password_policy;
    document.getElementById('password-policy-hint').textContent = policyHint(policy);

    const currentWrap = document.getElementById('current-password-wrap');
    const title = document.getElementById('password-form-title');
    if (user.has_password) {
      title.textContent = 'Смена пароля';
      currentWrap.hidden = false;
      currentWrap.querySelector('input').required = true;
    } else {
      title.textContent = 'Установка пароля';
      currentWrap.hidden = true;
      currentWrap.querySelector('input').required = false;
      currentWrap.querySelector('input').value = '';
    }
  }

  async function init() {
    try {
      const data = await api('/api/auth/profile');
      renderProfile(data);
    } catch (err) {
      if (err.message.includes('401') || err.code === 'unauthorized') {
        window.location.href = '/';
        return;
      }
      setStatus(err.message, true);
    }

    document.getElementById('profile-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      setStatus('');
      try {
        const form = e.target;
        const data = await api('/api/auth/profile', {
          method: 'PUT',
          body: JSON.stringify({ full_name: form.elements.full_name.value }),
        });
        setStatus('Профиль сохранён');
        renderProfile({ ...data.user, password_policy: (await api('/api/auth/password-policy')) });
      } catch (err) {
        setStatus(err.message, true);
      }
    });

    document.getElementById('password-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      setStatus('');
      const form = e.target;
      try {
        await api('/api/auth/change-password', {
          method: 'POST',
          body: JSON.stringify({
            current_password: form.elements.current_password?.value || '',
            new_password: form.elements.new_password.value,
            confirm_password: form.elements.confirm_password.value,
          }),
        });
        form.reset();
        setStatus('Пароль обновлён');
        const profile = await api('/api/auth/profile');
        renderProfile(profile);
      } catch (err) {
        setStatus(err.message, true);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
