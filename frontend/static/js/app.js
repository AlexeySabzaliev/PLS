// Портал ПЛС — вход и общие утилиты

async function plsJson(url, options = {}) {
  const r = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    credentials: 'same-origin',
    ...options,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
  return data;
}

async function plsLogin(email, password) {
  await plsJson('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  location.reload();
}

async function plsLogout() {
  await plsJson('/api/auth/logout', { method: 'POST' });
  location.reload();
}

async function plsTrySso(errEl) {
  const form = document.getElementById('login-form');
  if (!form) return;
  try {
    const cfg = await fetch('/api/auth/sso/config', { credentials: 'same-origin' }).then((r) => r.json());
    if (!cfg.enabled) return;
    const r = await fetch('/api/auth/sso/attempt', { method: 'POST', credentials: 'same-origin' });
    if (r.ok) {
      location.reload();
      return;
    }
    const data = await r.json().catch(() => ({}));
    if (data.pending_request && errEl) {
      errEl.textContent = data.message || 'Заявка на доступ отправлена администратору';
    }
  } catch (_) {
    /* SSO недоступен — остаётся форма пароля */
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('login-form');
  const errEl = document.getElementById('login-error');

  if (form) {
    plsTrySso(errEl);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (errEl) errEl.textContent = '';
      const email = form.elements.email.value.trim();
      const password = form.elements.password.value;
      try {
        await plsLogin(email, password);
      } catch (err) {
        if (errEl) errEl.textContent = err.message === 'invalid_credentials'
          ? 'Неверный email или пароль'
          : err.message;
      }
    });
  }
});
