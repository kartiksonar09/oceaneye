/**
 * ThemeContext.tsx
 * ────────────────
 * Manages dark/light theme state with:
 *   1. Respects `prefers-color-scheme` on first load if no explicit choice saved
 *   2. Persists explicit choice in localStorage under 'oceaneye_theme'
 *   3. Applies the class to <html> directly (works with Tailwind darkMode:'class')
 *   4. Exposes `theme` and `toggleTheme` to the whole app via context
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

type Theme = 'dark' | 'light';
const STORAGE_KEY = 'oceaneye_theme';

function resolveInitialTheme(): Theme {
  // 1. Explicit user choice takes priority
  const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
  if (stored === 'dark' || stored === 'light') return stored;
  // 2. System preference as fallback
  if (window.matchMedia('(prefers-color-scheme: light)').matches) return 'light';
  return 'dark'; // ocean eye default
}

function applyTheme(theme: Theme) {
  const html = document.documentElement;
  if (theme === 'light') {
    html.classList.remove('dark');
    html.classList.add('light');
  } else {
    html.classList.remove('light');
    html.classList.add('dark');
  }
}

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: 'dark',
  toggleTheme: () => {},
});

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<Theme>(() => {
    // Sync with what index.html inline script already set to avoid FOUC
    const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
    if (stored === 'dark' || stored === 'light') return stored;
    if (window.matchMedia('(prefers-color-scheme: light)').matches) return 'light';
    return 'dark';
  });

  // Apply on first mount and whenever theme changes
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // Track OS preference changes only if no explicit choice saved
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: light)');
    const handler = (e: MediaQueryListEvent) => {
      if (!localStorage.getItem(STORAGE_KEY)) {
        const next: Theme = e.matches ? 'light' : 'dark';
        setTheme(next);
      }
    };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next: Theme = prev === 'dark' ? 'light' : 'dark';
      localStorage.setItem(STORAGE_KEY, next);
      return next;
    });
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);
