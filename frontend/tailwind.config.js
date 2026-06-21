/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      colors: {
        telkom: {
          red: "#E81E28",
          dark: "#c8161f",
          gray: "#6b7280",
        },
        c3mr: {
          bg: "#f8fafc",
          surface: "#ffffff",
          border: "#e2e8f0",
          text: "#0f172a",
          muted: "#64748b",
          brand: "#E81E28",
          success: "#16a34a",
          warning: "#d97706",
          danger: "#dc2626",
        },
      },
    },
  },
  plugins: [],
};
