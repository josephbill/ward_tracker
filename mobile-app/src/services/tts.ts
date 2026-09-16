/**
 * Text-to-speech for accessibility (Section 9, item 2: "audio reading for
 * projects in translated languages, for blind personas or readers
 * preferring voice"). Uses expo-speech, which wraps the OS's own TTS engine
 * — works in Expo Go on both platforms, no dev client needed.
 *
 * Kikamba has no standard locale code and no known device TTS voice, so we
 * deliberately do NOT attempt to speak it — mispronouncing a language badly
 * is worse for an accessibility feature than clearly saying it isn't
 * available yet. English and Kiswahili are checked against the device's
 * actual installed voices before offering the "Listen" button, since
 * coverage varies by device/OS.
 */
import * as Speech from "expo-speech";
import { Lang } from "../i18n/i18n";

const LOCALE_BY_LANG: Partial<Record<Lang, string[]>> = {
  en: ["en-US", "en-GB", "en"],
  sw: ["sw-KE", "sw-TZ", "sw"],
  // kam: intentionally omitted — no supported device voice.
};

let voiceCache: Speech.Voice[] | null = null;

async function getVoices(): Promise<Speech.Voice[]> {
  if (voiceCache) return voiceCache;
  try {
    voiceCache = await Speech.getAvailableVoicesAsync();
  } catch {
    voiceCache = [];
  }
  return voiceCache;
}

export async function isTtsAvailableForLang(lang: Lang): Promise<boolean> {
  const candidates = LOCALE_BY_LANG[lang];
  if (!candidates) return false; // kam
  const voices = await getVoices();
  if (voices.length === 0) return true; // can't enumerate on this platform (e.g. web) — assume the OS/browser will handle it
  return voices.some((v) => candidates.some((c) => v.language?.toLowerCase().startsWith(c.toLowerCase())));
}

export function speak(text: string, lang: Lang, onDone?: () => void): void {
  const candidates = LOCALE_BY_LANG[lang];
  const language = candidates ? candidates[0] : undefined;
  Speech.speak(text, { language, onDone, onStopped: onDone, onError: onDone });
}

export function stopSpeaking(): void {
  Speech.stop();
}

export function isSpeakingAsync(): Promise<boolean> {
  return Speech.isSpeakingAsync();
}
