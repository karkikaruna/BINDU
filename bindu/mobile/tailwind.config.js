/** Design tokens come from the BINDU spec palette (section 10). */
module.exports = {
  darkMode: 'class',
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        forest: { DEFAULT: "#174C3C", 50: "#E8F0EC", 100: "#CFE1D9", 700: "#12392E" },
        himalaya: { DEFAULT: "#387A9B", 50: "#E6F0F5" },
        cream: "#F7F3E8",
        terracotta: { DEFAULT: "#C76B45", dark: "#A8552F", 50: "#F8E9E2" },
        charcoal: "#202723",
        marigold: "#E8A33D",
        danger: "#B3261E",
        line: "#E3DDCB",
        muted: "#5C665F",
      },
      fontFamily: {},
    },
  },
  plugins: [],
};


