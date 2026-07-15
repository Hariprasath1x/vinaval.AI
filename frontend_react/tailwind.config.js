/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Plus Jakarta Sans', 'Inter', 'sans-serif'],
      },
      colors: {
        brand: {
          50: '#f0f4ff',
          100: '#e0eaff',
          200: '#c7d9ff',
          300: '#a3bfff',
          400: '#7c9fff',
          500: '#5b7fff',
          600: '#4060f0',
          700: '#3248d4',
          800: '#2a3baa',
          900: '#263587',
          950: '#161f52',
        },
        surface: {
          900: '#0a0e1a',
          800: '#0f1425',
          700: '#141a2e',
          600: '#1a2240',
          500: '#202a4e',
        },
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(135deg, #5b7fff 0%, #a78bfa 100%)',
        'gradient-hero': 'linear-gradient(135deg, #0a0e1a 0%, #141a2e 50%, #0f1425 100%)',
        'gradient-card': 'linear-gradient(135deg, rgba(91,127,255,0.1) 0%, rgba(167,139,250,0.05) 100%)',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-up': 'fadeUp 0.6s ease-out forwards',
        'fade-in': 'fadeIn 0.4s ease-out forwards',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
    },
  },
  plugins: [],
}
