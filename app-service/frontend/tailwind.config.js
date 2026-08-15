/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef4ff',
          100: '#d9e6ff',
          500: '#2f6fed',
          600: '#2359d1',
          700: '#1c47a8',
        },
        surface: '#f5f7fb',
        panel: '#ffffff',
        border: '#e5e9f2',
        muted: '#8a93a6',
        critical: '#e5484d',
        warning: '#f5a623',
        success: '#2ecc71',
        info: '#3aa0ff',
      },
      boxShadow: {
        card: '0 1px 2px rgba(16,24,40,0.04), 0 1px 3px rgba(16,24,40,0.06)',
      },
      borderRadius: {
        xl2: '14px',
      },
    },
  },
  plugins: [],
}
