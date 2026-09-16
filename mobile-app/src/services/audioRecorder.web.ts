/**
 * Web stub — see audioRecorder.ts's docstring for why this file exists at
 * all (expo-av's own web build is broken in the installed SDK 51 version).
 * Never actually called: VoiceInputButton uses the Web Speech API directly
 * on web and only reaches these functions on native platforms. Metro's
 * platform-extension resolution picks this file over audioRecorder.ts when
 * bundling for web, which is what keeps the broken expo-av web module out
 * of the bundle graph entirely.
 */
export async function requestPermission(): Promise<boolean> {
  return false;
}

export async function startRecording(): Promise<void> {
  throw new Error("Native audio recording is not available on web — use the Web Speech API path instead.");
}

export async function stopRecording(): Promise<string | null> {
  return null;
}

export const isSupported = false;
