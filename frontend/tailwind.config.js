/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["'Sora'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
        display: ["'Cabinet Grotesk'", "'Sora'", "sans-serif"],
      },
      colors: {
        bg: "#0A0A0F",
        surface: "#12121A",
        border: "#1E1E2E",
        accent: "#6C63FF",
        "accent-light": "#8B85FF",
        success: "#22C55E",
        warning: "#F59E0B",
        danger: "#EF4444",
        muted: "#4A4A6A",
        text: "#E8E8F0",
        "text-dim": "#8888AA",
      },
      animation: {
        "fade-up": "fadeUp 0.5s ease forwards",
        "pulse-slow": "pulse 3s ease-in-out infinite",
        shimmer: "shimmer 2s linear infinite",
      },
      keyframes: {
        fadeUp: {
          from: { opacity: 0, transform: "translateY(16px)" },
          to: { opacity: 1, transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};
