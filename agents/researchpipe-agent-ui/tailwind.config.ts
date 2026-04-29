import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['ui-monospace', 'SF Mono', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      colors: {
        ink: { DEFAULT: "#0F172A", light: "#1E293B", muted: "#475569" },
        accent: { DEFAULT: "#0F172A", hover: "#1E40AF" },
      },
    },
  },
  plugins: [],
};

export default config;
