/**
 * Analytics via Sabilytics (https://www.sabilytics.com/) — item 4 of the
 * "best experience" follow-up.
 *
 * IMPORTANT LIMITATION: Sabilytics is a WEB-ONLY analytics platform. Its
 * public site documents a <script> snippet for websites and a
 * `sabilytics.track(event, props)` JS API — there is no React Native/Expo
 * SDK and no server-side ingestion API for the Flask backend. So:
 *
 *   - On the web build (`expo start --web` / a real web deploy), this loads
 *     the Sabilytics tracker script once and forwards trackEvent() calls to
 *     `window.sabilytics.track(...)`.
 *   - On native (Android/iOS), there is nothing Sabilytics-side to call —
 *     trackEvent() is a no-op there (logged in dev mode only, so event
 *     instrumentation throughout the app is still visible/testable without
 *     a real analytics account). If native analytics is needed later, a
 *     cross-platform service (Amplitude/Segment/Mixpanel, all of which ship
 *     a real RN SDK) would sit behind this exact same trackEvent() call —
 *     every call site in the app already goes through this one module.
 *
 * Configure via EXPO_PUBLIC_SABILYTICS_SITE_ID / EXPO_PUBLIC_SABILYTICS_DOMAIN
 * / EXPO_PUBLIC_SABILYTICS_SCRIPT_URL once a real Sabilytics account exists
 * (the script src is account-specific and wasn't publicly documented at
 * integration time — see this file's git history / PR description for what
 * was actually checked). Until then this is intentionally inert: no script
 * is injected and no network call is made, matching the rest of this repo's
 * "stub until credentials exist" pattern (ledger, WhatsApp, SMS).
 */
import { Platform } from "react-native";

const SITE_ID = process.env.EXPO_PUBLIC_SABILYTICS_SITE_ID;
const DOMAIN = process.env.EXPO_PUBLIC_SABILYTICS_DOMAIN;
const SCRIPT_URL = process.env.EXPO_PUBLIC_SABILYTICS_SCRIPT_URL;

let webScriptLoaded = false;

function ensureWebScriptLoaded(): void {
  if (Platform.OS !== "web" || webScriptLoaded) return;
  if (!SITE_ID || !DOMAIN || !SCRIPT_URL) return; // not configured — stay inert
  if (typeof document === "undefined") return;

  const script = document.createElement("script");
  script.async = true;
  script.src = SCRIPT_URL;
  script.setAttribute("data-site", SITE_ID);
  script.setAttribute("data-domain", DOMAIN);
  document.head.appendChild(script);
  webScriptLoaded = true;
}

export function initAnalytics(): void {
  ensureWebScriptLoaded();
}

export function trackEvent(name: string, props?: Record<string, unknown>): void {
  if (Platform.OS === "web") {
    ensureWebScriptLoaded();
    const sabilytics = (globalThis as any).sabilytics;
    if (typeof sabilytics?.track === "function") {
      sabilytics.track(name, props);
    }
    return;
  }

  // Native: no Sabilytics SDK exists. Log in dev only so event
  // instrumentation is verifiable during development without a real
  // analytics backend on any platform.
  if (__DEV__) {
    // eslint-disable-next-line no-console
    console.log(`[analytics:noop-native] ${name}`, props ?? {});
  }
}
