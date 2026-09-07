/** Общие утилиты UI УЗнТ */
const UznApi = {
  ERROR_MESSAGES: {
    forbidden: 'Нет доступа к этому разделу',
    unauthorized: 'Войдите в систему (email и пароль)',
    not_found: 'Не найдено',
    validation: 'Проверьте правильность заполнения полей',
    invalid_date: 'Неверный формат даты',
  },

  esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  },

  formatError(data, fallback) {
    if (!data) return fallback || 'Ошибка запроса';
    if (data.message) return data.message;
    const code = data.error;
    if (code && this.ERROR_MESSAGES[code]) return this.ERROR_MESSAGES[code];
    return code || fallback || 'Ошибка запроса';
  },

  async json(url, options = {}) {
    const r = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      credentials: 'same-origin',
      ...options,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      const err = new Error(this.formatError(data, `HTTP ${r.status}`));
      err.data = data;
      err.status = r.status;
      throw err;
    }
    return data;
  },

  today() {
    const n = new Date();
    const m = String(n.getMonth() + 1).padStart(2, '0');
    const d = String(n.getDate()).padStart(2, '0');
    return `${n.getFullYear()}-${m}-${d}`;
  },
};