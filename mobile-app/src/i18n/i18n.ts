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

// Maps the backend's `{"error": "<code>"}` body (see backend/app/api/*.py)
// to a translated, resident-facing sentence. Without this, a failed
// request-otp/submit-issue call showed the raw API error code itself (e.g.
// "ledger_unavailable") as the alert body — meaningless to a non-technical
// reader and untranslated regardless of selected language.
const API_ERROR_KEYS: Record<string, string> = {
  ledger_unavailable: "error_ledger_unavailable",
  phone_not_verified: "error_phone_not_verified",
  rate_limited: "error_rate_limited",
  unknown_project: "error_unknown_project",
  invalid_or_expired_code: "otpMismatchError",
};

export function translateApiError(lang: Lang, message?: string): string {
  const key = message ? API_ERROR_KEYS[message] : undefined;
  return t(lang, key ?? "error_generic");
}
