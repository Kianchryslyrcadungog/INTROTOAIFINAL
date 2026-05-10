/**
 * Aegis theme controller
 * Handles persistent light/dark theme toggling across pages.
 */
(function () {
  const STORAGE_KEY = 'aegis-theme';
  const root = document.documentElement;

  function getPreferredTheme() {
    const savedTheme = localStorage.getItem(STORAGE_KEY);
    if (savedTheme === 'light' || savedTheme === 'dark') {
      return savedTheme;
    }

    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function setToggleLabel(toggleButton, activeTheme) {
    const code = toggleButton.querySelector('[data-theme-code]');
    const label = toggleButton.querySelector('[data-theme-label]');

    if (!code || !label) {
      return;
    }

    const isDark = activeTheme === 'dark';
    code.textContent = isDark ? 'LM' : 'DM';
    label.textContent = isDark ? 'Light Mode' : 'Dark Mode';
    toggleButton.setAttribute('aria-pressed', String(isDark));
  }

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    root.style.colorScheme = theme;

    document.querySelectorAll('[data-theme-toggle]').forEach((toggleButton) => {
      setToggleLabel(toggleButton, theme);
    });
  }

  function toggleTheme() {
    const currentTheme = root.getAttribute('data-theme') || getPreferredTheme();
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';

    applyTheme(nextTheme);
    localStorage.setItem(STORAGE_KEY, nextTheme);
  }

  const initialTheme = getPreferredTheme();
  applyTheme(initialTheme);

  document.querySelectorAll('[data-theme-toggle]').forEach((toggleButton) => {
    toggleButton.addEventListener('click', toggleTheme);
  });
})();
