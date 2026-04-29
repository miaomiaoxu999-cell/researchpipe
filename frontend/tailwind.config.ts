import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // McKinsey-style palette
        navy: {
          DEFAULT: "#051C2C",
          900: "#051C2C",
          800: "#0A2540",
          700: "#13294B",
          600: "#1F3A5F",
        },
        accent: {
          DEFAULT: "#2251FF",
          hover: "#1A3FCC",
        },
        ink: "#051C2C",
        cream: "#FBFBF7",
        warm: "#F5F2EC",
        line: "#E6E2DA",
        muted: "#6B7280",
        background: "#FFFFFF",
        foreground: "#051C2C",
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "Noto Serif SC", "serif"],
        sans: [
          "var(--font-sans)",
          "Inter",
          "Source Han Sans SC",
          "Noto Sans SC",
          "system-ui",
          "sans-serif",
        ],
        mono: ["var(--font-mono)", "JetBrains Mono", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        tightest: "-0.04em",
      },
      maxWidth: {
        page: "1200px",
        prose: "68ch",
      },
      boxShadow: {
        card: "0 1px 2px rgba(5,28,44,0.04), 0 0 0 1px rgba(5,28,44,0.06)",
        cardHover: "0 8px 24px rgba(5,28,44,0.08), 0 0 0 1px rgba(5,28,44,0.10)",
      },
    },
  },
  plugins: [typography],
};
export default config;
