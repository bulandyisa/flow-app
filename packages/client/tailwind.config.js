/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Тёмная тема, вдохновлённая текущим дашбордом
        surface: {
          DEFAULT: '#1A1D26',
          light: '#242830',
          lighter: '#2E323C',
        },
        accent: {
          DEFAULT: '#6366F1', // indigo
          hover: '#818CF8',
        },
        success: '#22C55E',
        warning: '#F59E0B',
        danger: '#EF4444',
      },
    },
  },
  plugins: [],
};
