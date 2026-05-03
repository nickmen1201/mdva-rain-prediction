import { useEffect, useState } from 'react';

const ICONS = { dark: '☀️', light: '🌙' };

export default function ThemeToggle() {
  const [theme, setTheme] = useState(
    () => localStorage.getItem('mdva-theme') ?? 'dark'
  );

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('mdva-theme', theme);
  }, [theme]);

  const toggle = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  return (
    <button
      className="theme-toggle"
      onClick={toggle}
      title={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
      aria-label="Cambiar tema"
    >
      {ICONS[theme]}
    </button>
  );
}
