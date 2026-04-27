/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        tonic: '#3b82f6',
        dominant: '#ef4444',
        subdominant: '#10b981',
        tritone: '#f97316',
      },
    },
  },
  plugins: [],
};
