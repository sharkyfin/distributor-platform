module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/*.html",
    "./apps/**/*.py",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f6f7f8",
          100: "#eceff1",
          200: "#d4dbe0",
          300: "#aab7c2",
          400: "#788896",
          500: "#586674",
          600: "#44515d",
          700: "#343e47",
          800: "#222a31",
          900: "#161b1f"
        },
        steel: {
          100: "#f4f5f6",
          200: "#e7ebee",
          300: "#d0d7dc",
          400: "#acb7c0",
          500: "#7a8794"
        },
        signal: {
          500: "#a86134",
          600: "#8d4f2a"
        }
      },
      boxShadow: {
        soft: "0 16px 48px rgba(22, 27, 31, 0.08)"
      },
      fontFamily: {
        sans: ["Manrope", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
};

