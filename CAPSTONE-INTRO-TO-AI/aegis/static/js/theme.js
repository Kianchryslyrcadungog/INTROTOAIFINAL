/**
 * Aegis shared theme controls.
 * Persists dark/light mode and keeps the nav toggle in sync.
 */

(function () {
  const storageKey = 'aegis-theme';

  function getPreferredTheme() {
    const savedTheme = localStorage.getItem(storageKey);
    if (savedTheme === 'light' || savedTheme === 'dark') {
      return savedTheme;
    }
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    document.body.dataset.theme = theme;
    localStorage.setItem(storageKey, theme);

    document.querySelectorAll('[data-theme-label]').forEach(label => {
      label.textContent = theme === 'light' ? 'Light' : 'Dark';
    });

    document.querySelectorAll('[data-theme-toggle]').forEach(toggle => {
      toggle.setAttribute('aria-pressed', theme === 'light' ? 'true' : 'false');
    });
  }

  function toggleTheme() {
    const nextTheme = document.body.dataset.theme === 'light' ? 'dark' : 'light';
    applyTheme(nextTheme);
  }

  function init() {
    if (!document.body) {
      return;
    }

    if (!document.body.dataset.theme) {
      applyTheme(getPreferredTheme());
    }

    document.querySelectorAll('[data-theme-toggle]').forEach(toggle => {
      if (toggle.dataset.bound === 'true') {
        return;
      }

      toggle.dataset.bound = 'true';
      toggle.addEventListener('click', toggleTheme);
    });
  }

  window.AegisTheme = { init, applyTheme };

  document.addEventListener('DOMContentLoaded', init, { once: true });
})();