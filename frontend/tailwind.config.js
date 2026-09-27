/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // Landing page palette. The chat drawer keeps Tailwind's stone/amber.
      colors: {
        linen: "#f6f2ea",
        ink: "#1f211b",
        olive: { DEFAULT: "#46552a", dark: "#35411f", soft: "#e6e9da" },
        tomato: { DEFAULT: "#b3402b", dark: "#933322" },
        muted: "#686a5f",
        rule: "#d9d2c3",
      },
      fontFamily: {
        display: ['"DM Serif Display"', "Georgia", '"Times New Roman"', "serif"],
        body: ["Karla", "-apple-system", "BlinkMacSystemFont", '"Segoe UI"', "sans-serif"],
      },
    },
  },
  plugins: [],
};
