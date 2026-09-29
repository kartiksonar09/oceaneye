/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // ─── Radar surface palette ────────────────────────────────────────────
        // All values reference CSS custom properties defined in index.css.
        // Swapping :root vs .light vars is all that's needed for theme switching.
        radar: {
          950: 'var(--radar-950)',
          900: 'var(--radar-900)',
          850: 'var(--radar-850)',
          800: 'var(--radar-800)',
          750: 'var(--radar-750)',
          700: 'var(--radar-700)',
          600: 'var(--radar-600)',
          500: 'var(--radar-500)',
          400: 'var(--radar-400)',
          300: 'var(--radar-300)',
          200: 'var(--radar-200)',
          100: 'var(--radar-100)',
        },
        // ─── Semantic accents (same hue families, adjusted for contrast) ──────
        spill: {
          DEFAULT:  'var(--spill-default)',
          amber:    'var(--spill-amber)',
          glow:     'var(--spill-glow)',
          border:   'var(--spill-border)',
          dark:     'var(--spill-dark)',
        },
        vessel: {
          DEFAULT: 'var(--vessel-default)',
          teal:    'var(--vessel-teal)',
          cyan:    'var(--vessel-cyan)',
          track:   'var(--vessel-track)',
        },
        suspect: {
          DEFAULT: 'var(--suspect-default)',
          crimson: 'var(--suspect-crimson)',
          ring:    'var(--suspect-ring)',
          glow:    'var(--suspect-glow)',
        },
        status: {
          active:     '#F59E0B',
          monitoring: '#38BDF8',
          resolved:   '#10B981',
          danger:     '#EF4444',
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"IBM Plex Mono"', 'ui-monospace', 'monospace'],
        sans: ['"IBM Plex Sans"', '"Space Grotesk"', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'none': '0px',
        'xs': '2px',
        'sm': '3px',
        'DEFAULT': '4px',
        'md': '4px',
        'lg': '6px',
      },
      letterSpacing: {
        tighter: '-0.04em',
        tight: '-0.02em',
        normal: '0',
        wide: '0.04em',
        wider: '0.08em',
        widest: '0.12em',
      },
      animation: {
        'radar-pulse': 'radar-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'beacon': 'beacon 1.5s ease-in-out infinite',
      },
      keyframes: {
        'radar-pulse': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.4', transform: 'scale(1.08)' },
        },
        'beacon': {
          '0%': { transform: 'scale(0.95)', opacity: '0.8' },
          '50%': { transform: 'scale(1.4)', opacity: '0' },
          '100%': { transform: 'scale(0.95)', opacity: '0' },
        },
      },
    },
  },
  plugins: [],
}
