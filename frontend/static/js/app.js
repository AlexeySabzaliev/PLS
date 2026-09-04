// Портал ПЛС — вход, регистрация, восстановление пароля

async function plsJson(url, options = {}) {
  const r = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    credentials: 'same-origin',
    ...options,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const err = new Error(data.message || data.error || `HTTP ${r.status}`);
    err.code = data.error;
    err.payload = data;
    throw err;
  }
  return data;
}

async function plsLogin(email, password) {
  await plsJson('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  location.reload();
}

function showLoginPanel(mainPanel, registerPanel, resetPanel) {
  if (registerPanel) registerPanel.hidden = true;
  if (resetPanel) resetPanel.hidden = true;
  if (mainPanel) mainPanel.hidden = false;
}

document.addEventListener('DOMContentLoaded', async () => {
  const mainPanel = document.getElementById('login-main-panel');
  const registerPanel = document.getElementById('login-register-panel');
  const resetPanel = document.getElementById('login-reset-panel');
  const form = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const resetForm = document.getElementById('reset-form');
  const errEl = document.getElementById('login-error');
  const infoEl = document.getElementById('login-info');

  function clearStatus() {
    if (errEl) errEl.textContent = '';
    if (infoEl) infoEl.textContent = '';
  }

  const [regPolicy] = await Promise.all([
    fetch('/api/auth/register-policy', { credentials: 'same-origin' }).then((r) => r.json()).catch(() => null),
  ]);

  const regPwHint = document.getElementById('register-password-hint');
  const policy = regPolicy?.password_policy;
  if (regPwHint && policy?.min_length) {
    regPwHint.textContent = `Пароль: не менее ${policy.min_length} символов, буква и цифра.`;
  }

  const btnRegister = document.getElementById('btn-show-register');
  if (btnRegister && regPolicy?.enabled === false) {
    btnRegister.hidden = true;
  }

  document.getElementById('btn-show-register')?.addEventListener('click', () => {
    clearStatus();
    mainPanel.hidden = true;
    resetPanel.hidden = true;
    registerPanel.hidden = false;
    const loginEmail = form?.elements.email?.value?.trim();
    if (loginEmail && registerForm?.elements.email) {
      registerForm.elements.email.value = loginEmail;
    }
  });

  document.getElementById('btn-register-to-login')?.addEventListener('click', () => {
    clearStatus();
    showLoginPanel(mainPanel, registerPanel, resetPanel);
  });

  document.getElementById('btn-show-reset')?.addEventListener('click', () => {
    clearStatus();
    mainPanel.hidden = true;
    registerPanel.hidden = true;
    resetPanel.hidden = false;
    const loginEmail = form?.elements.email?.value?.trim();
    if (loginEmail && resetForm?.elements.email) {
      resetForm.elements.email.value = loginEmail;
    }
  });

  document.getElementById('btn-show-login')?.addEventListener('click', () => {
    clearStatus();
    showLoginPanel(mainPanel, registerPanel, resetPanel);
  });

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearStatus();
    try {
      await plsLogin(form.elements.email.value.trim(), form.elements.password.value);
    } catch (err) {
      if (errEl) {
        errEl.textContent = err.payload?.message || (
          err.code === 'invalid_credentials' ? 'Неверный email или пароль' : err.message
        );
      }
    }
  });

  registerForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearStatus();
    try {
      const data = await plsJson('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          email: registerForm.elements.email.value.trim(),
          full_name: registerForm.elements.full_name.value.trim(),
          password: registerForm.elements.password.value,
          confirm_password: registerForm.elements.confirm_password.value,
        }),
      });
      if (infoEl) infoEl.textContent = data.message || 'Регистрация выполнена.';
      location.reload();
    } catch (err) {
      if (errEl) errEl.textContent = err.payload?.message || err.message;
    }
  });

  resetForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearStatus();
    try {
      const data = await plsJson('/api/auth/password-reset/request', {
        method: 'POST',
        body: JSON.stringify({
          email: resetForm.elements.email.value.trim(),
          note: resetForm.elements.note.value.trim(),
        }),
      });
      if (infoEl) infoEl.textContent = data.message || 'Заявка отправлена.';
      showLoginPanel(mainPanel, registerPanel, resetPanel);
    } catch (err) {
      if (errEl) errEl.textContent = err.message;
    }
  });
});
