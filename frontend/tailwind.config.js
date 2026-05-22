/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        c3mr: {
          bg: "#f8fafc",
          surface: "#ffffff",
          border: "#e2e8f0",
          text: "#0f172a",
          muted: "#64748b",
          brand: "#2563eb",
          success: "#16a34a",
          warning: "#d97706",
          danger: "#dc2626",
        },
      },
    },
  },
  plugins: [],
};
