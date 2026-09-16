/**
 * Native (Android/iOS) audio recording, used by VoiceInputButton's native
 * fallback path. Kept in its own module — with a audioRecorder.web.ts
 * sibling — because expo-av's own web build has a broken internal import in
 * the installed SDK 51 version (ExponentAV.web.js imports a
 * ./Audio/RecordingConstants file that isn't shipped in the package),
 * which crashes Metro's whole web bundle if `expo-av` is imported
 * anywhere reachable from the web entry point — even behind a
 * `Platform.OS !== "web"` runtime check, since Metro still has to resolve
 * the import statically. React Native's platform-extension resolution
 * (`.web.ts` beats the bare file on web) is what actually keeps expo-av
 * out of the web bundle, not a runtime branch — see audioRecorder.web.ts.
 */
import { Audio } from "expo-av";

let activeRecording: Audio.Recording | null = null;

export async function requestPermission(): Promise<boolean> {
  const permission = await Audio.requestPermissionsAsync();
  return permission.granted;
}

export async function startRecording(): Promise<void> {
  await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
  const { recording } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
  activeRecording = recording;
}

export async function stopRecording(): Promise<string | null> {
  const recording = activeRecording;
  if (!recording) return null;
  await recording.stopAndUnloadAsync();
  activeRecording = null;
  return recording.getURI();
}

export const isSupported = true;
