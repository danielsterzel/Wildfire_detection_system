/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Montserrat', 'sans-serif']
      },
      keyframes: {
        fadeUp: {
          '0%': {opacity: '0', transform: 'translateY(40px)'},
          '100%': {opacity: '1', transform: 'translateY(0)'}
        },
        fadeOutUp: {
          '0%': {opacity: '1', transform: 'translateY(0)'},
          '100%': {opacity: '0', transform: 'translateY(-160px)'}
        },
        fadeDown: {
        '0%': {opacity: '0', transform: 'translateY(-40px)'},
        '100%': {opacity: '1', transform: 'translateY(0)'}
        },
        fadeOutDown: {
          '0%': {opacity: '1', transform: 'translateY(0)'},
          '100%': {opacity: '0', transform: 'translateY(40px)'}
        },
        gridFadeUp: {
          '0%': {opacity: '0', transform: 'translateY(200px)'},
          '100%': {opacity: '1', transform: 'translateY(0)'}
        }
      },
      animation: {
        fadeUp: 'fadeUp 0.8s ease-out forwards',
        fadeOutUp: 'fadeOutUp 0.8s ease-out forwards',
        fadeDown: 'fadeDown 0.8s ease-out forwards',
        fadeOutDown: 'fadeOutDown 0.8s ease-out forwards',
        gridFadeUp: 'gridFadeUp 0.7s ease-out 1s forwards'

      }
    },
  },
  plugins: [],
}

