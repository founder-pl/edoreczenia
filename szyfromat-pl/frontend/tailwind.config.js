/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'pp-red': '#E30613',
        'pp-dark': '#050049',
        'pp-gray': '#4d4d4d',
      },
    },
  },
  plugins: [],
}
