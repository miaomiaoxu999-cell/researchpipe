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
        // Tavily-inspired warm cream palette
        cream: {
          DEFAULT: "#FEFCF5",
          50: "#FFFCF6",
          100: "#FEFCF5",
          200: "#F9F7F2",
          300: "#F7F7F5",
          400: "#EDE6DB",
        },
        ink: {
          DEFAULT: "#3C3A39", // warm dark gray (Tavily body text)
          900: "#1F1E1E",
          800: "#3C3A39",
          700: "#605D5B",
          600: "#807D7B",
        },
        accent: {
          DEFAULT: "#81B09A",
          green: "#81B09A",
          blue: "#3860BE",
          link: "#2677FF",
          navy: "#27455C",
        },
        line: "rgba(11,9,7,0.08)",
        muted: "rgba(11,9,7,0.62)",
        soft: "rgba(11,9,7,0.05)",
        // Legacy tokens kept for compat
        navy: { DEFAULT: "#3C3A39", 900: "#1F1E1E", 800: "#3C3A39", 700: "#605D5B", 600: "#807D7B" },
        warm: "#F7F7F5",
        background: "#FEFCF5",
        foreground: "#3C3A39",
      },
      fontFamily: {
        sans: [
          "var(--font-sans)",
          "Inter",
          "PingFang SC",
          "Hiragino Sans GB",
          "Noto Sans SC",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        serif: [
          "var(--font-serif)",
          "Inter",
          "PingFang SC",
          "Hiragino Sans GB",
          "Noto Sans SC",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        mono: [
          "var(--font-mono)",
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
      letterSpacing: {
        tightest: "-0.04em",
        hero: "-0.02em",
      },
      maxWidth: {
        page: "1200px",
        prose: "68ch",
        narrow: "720px",
      },
      borderRadius: {
        card: "12px",
        chip: "999px",
        btn: "10px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(11,9,7,0.04), 0 0 0 1px rgba(11,9,7,0.06)",
        cardHover: "0 8px 24px rgba(11,9,7,0.08), 0 0 0 1px rgba(11,9,7,0.10)",
        float: "0 24px 60px -20px rgba(11,9,7,0.18), 0 8px 20px -10px rgba(11,9,7,0.10)",
      },
      backgroundImage: {
        "landscape-fade":
          "linear-gradient(#FEFCF5 0%, #FEFCF5 8%, rgba(254,252,245,0.85) 35%, rgba(254,252,245,0) 100%)",
      },
    },
  },
  plugins: [typography],
};
export default config;
