import typography from "@tailwindcss/typography";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#14171F",
        body: "#3D4350",
        muted: "#5B6270",
        line: "#E3E6EC",
        line2: "#D5D9E0",
        ground: "#F6F7F9",
        accent: { DEFAULT: "#2453D6", dark: "#1A3FA8", soft: "#EAF0FF", line: "#DCE4FB" },
        ok: { DEFAULT: "#1F7A4D", dark: "#17613C", soft: "#E6F4EC" },
        yt: { bg: "#FDECEC", fg: "#A1251B" },
        cs: { bg: "#E8EEFF", fg: "#1D46B8" },
        ud: { bg: "#F1EAFE", fg: "#5B21B6" },
        pp: { bg: "#FFF1DB", fg: "#7A4500" },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["'Space Grotesk'", "Inter", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [typography],
};
