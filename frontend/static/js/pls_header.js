/** Шапка: меню профиля и выход */
(function initPlsHeader() {
  const toggle = document.getElementById('pls-profile-toggle');
  const dropdown = document.getElementById('pls-profile-dropdown');

  function closeProfileMenu() {
    if (!dropdown || !toggle) return;
    dropdown.classList.add('hidden');
    toggle.setAttribute('aria-expanded', 'false');
  }

  if (toggle && dropdown) {
    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      const willOpen = dropdown.classList.contains('hidden');
      closeProfileMenu();
      if (willOpen) {
        dropdown.classList.remove('hidden');
        toggle.setAttribute('aria-expanded', 'true');
      }
    });
    document.addEventListener('click', closeProfileMenu);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeProfileMenu();
    });
    dropdown.addEventListener('click', (e) => e.stopPropagation());
  }

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
