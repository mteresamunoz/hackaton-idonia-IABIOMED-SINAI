/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#bae2fd',
          300: '#7ccbfa',
          400: '#38b0f8',
          500: '#0ea0ea',
          600: '#0280c7',
          700: '#0366a1',
          800: '#075685',
          900: '#0c486e',
          950: '#082f49',
        }
      }
    },
  },
  plugins: [],
}
