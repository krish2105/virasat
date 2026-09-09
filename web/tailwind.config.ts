import type { Config } from "tailwindcss";

// Tokens derived from the city itself (MASTER-PROMPT §13.2). One accent: --alarm,
// which appears only on a flagged change.
const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        sandstone: "rgb(var(--sandstone) / <alpha-value>)",
        plaster: "rgb(var(--plaster) / <alpha-value>)",
        indigo: "rgb(var(--indigo) / <alpha-value>)",
        ink: "rgb(var(--ink) / <alpha-value>)",
        alarm: "rgb(var(--alarm) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        ground: "rgb(var(--ground) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        line: "rgb(var(--line) / <alpha-value>)",
        fg: "rgb(var(--fg) / <alpha-value>)",
        "fg-muted": "rgb(var(--fg-muted) / <alpha-value>)",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      // Nine chowkris: a 9-column layout grid the sections snap to.
      gridTemplateColumns: { chowkri: "repeat(9, minmax(0, 1fr))" },
      borderWidth: { 3: "3px" },
    },
  },
  plugins: [],
};

export default config;
