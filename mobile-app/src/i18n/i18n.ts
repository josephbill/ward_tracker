import en from "./en.json";
import sw from "./sw.json";
import kam from "./kam.json";

export type Lang = "en" | "sw" | "kam";
// Kiswahili is the primary/default language; English remains a fully
// supported translation choice and is also the fallback for any missing
// key below (see t()'s DICTS.en fallback).
export const SUPPORTED_LANGUAGES: Lang[] = ["sw", "en", "kam"];

const DICTS: Record<Lang, Record<string, string>> = { en, sw, kam } as any;

export function t(lang: Lang, key: string, vars?: Record<string, string | number>): string {
  const dict = DICTS[lang] ?? DICTS.en;
  let template = dict[key] ?? DICTS.en[key] ?? key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      template = template.replace(`{${k}}`, String(v));
    }
  }
  return template;
}
