import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--dv-font-sans)'],
        mono: ['var(--dv-font-mono)'],
      },
      colors: {
        'dv-accent': 'var(--dv-accent)',
        'dv-bg': 'var(--dv-bg)',
        'dv-border': 'var(--dv-border)',
        'dv-text': 'var(--dv-text-primary)',
        'dv-muted': 'var(--dv-text-secondary)',
      },
      maxWidth: {
        'message': 'var(--dv-message-max-width)',
      },
      width: {
        'sidebar': 'var(--dv-sidebar-width)',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'blink': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        'pulse-dot': {
          '0%, 80%, 100%': { transform: 'scale(0)' },
          '40%': { transform: 'scale(1)' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'progress-fill': {
          '0%': { width: '0%' },
          '100%': { width: '100%' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.2s ease-out',
        'blink': 'blink 1s step-end infinite',
        'pulse-dot': 'pulse-dot 1.4s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
      },
    },
  },
  plugins: [],
}

export default config