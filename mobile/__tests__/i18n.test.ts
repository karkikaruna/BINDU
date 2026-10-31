jest.mock("@/lib/storage", () => ({ safeStorage: { getItem: async () => null, setItem: async () => undefined, removeItem: async () => undefined } }));
import { INTERESTS, LEVELS } from "@/constants/theme";
import { makeTranslator, translations } from "@/lib/i18n";

const placeholders = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort().join(",");
const keys = Object.keys(translations.en) as (keyof typeof translations.en)[];

describe("interface translations", () => {
  it("Nepali covers exactly the English keys, with no empty strings", () => {
    expect(Object.keys(translations.ne).sort()).toEqual([...keys].sort());
    for (const k of keys) expect(translations.ne[k].trim().length).toBeGreaterThan(0);
  });

  it("every translation keeps the same {placeholders} as the English text", () => {
    for (const k of keys) expect([k, placeholders(translations.ne[k])]).toEqual([k, placeholders(translations.en[k])]);
  });

  it("Nepali strings are really Devanagari, except for brand/unit tokens", () => {
    const untranslatedOk = new Set(["opt.Beginner"]); // none expected; guard stays explicit
    for (const k of keys) {
      if (untranslatedOk.has(k)) continue;
      expect([k, /[ऀ-ॿ]/.test(translations.ne[k])]).toEqual([k, true]);
    }
  });

  it("fills placeholders and leaves unknown ones visible instead of dropping them", () => {
    expect(makeTranslator("English")("home.welcome", { name: "KK" })).toBe("Welcome, KK");
    expect(makeTranslator("नेपाली")("home.welcome", { name: "KK" })).toBe("स्वागत छ, KK");
    expect(makeTranslator("English")("home.welcome")).toBe("Welcome, {name}");
  });

  it("option labels exist for every level and interest and fall back to the raw value", () => {
    const ne = makeTranslator("नेपाली");
    for (const v of [...LEVELS, ...INTERESTS]) expect(ne.opt(v)).not.toBe(v);
    expect(ne.opt("Some backend category")).toBe("Some backend category");
    expect(makeTranslator("English").opt("mid")).toBe("Mid-range");
  });
});
