/** Кнопка выхода в шапке портала */
(function initPlsHeader() {
  const btn = document.getElementById('pls-logout-btn');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (_) {
      /* всё равно уходим на главную */
    }
    window.location.href = '/';
  });
})();
